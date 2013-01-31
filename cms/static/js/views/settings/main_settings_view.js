if (!CMS.Views['Settings']) CMS.Views.Settings = {};

// TODO move to common place
CMS.Views.ValidatingView = Backbone.View.extend({
	// Intended as an abstract class which catches validation errors on the model and 
	// decorates the fields. Needs wiring per class, but this initialization shows how 
	// either have your init call this one or copy the contents
	initialize : function() {
		this.model.on('error', this.handleValidationError, this);
		this.selectorToField = _.invert(this.fieldToSelectorMap);
	},
	
	errorTemplate : _.template('<span class="message-error"><%= message %></span>'),

	events : {
		"blur input" : "clearValidationErrors",
		"blur textarea" : "clearValidationErrors"
	},
	fieldToSelectorMap : {
		// Your subclass must populate this w/ all of the model keys and dom selectors 
		// which may be the subjects of validation errors
	},
	_cacheValidationErrors : [],
	handleValidationError : function(model, error) {
		// error is object w/ fields and error strings
		for (var field in error) {
			var ele = this.$el.find('#' + this.fieldToSelectorMap[field]); 
			this._cacheValidationErrors.push(ele);
			if ($(ele).is('div')) {
				// put error on the contained inputs
				$(ele).find('input, textarea').addClass('error');
			}
			else $(ele).addClass('error');
			$(ele).parent().append(this.errorTemplate({message : error[field]}));
		}
	},
	
	clearValidationErrors : function() {
		// error is object w/ fields and error strings
		while (this._cacheValidationErrors.length > 0) {
			var ele = this._cacheValidationErrors.pop(); 
			if ($(ele).is('div')) {
				// put error on the contained inputs
				$(ele).find('input, textarea').removeClass('error');
			}
			else $(ele).removeClass('error');
			$(ele).nextAll('.message-error').remove();
		}
	},
	
	saveIfChanged : function(event) {
		// returns true if the value changed and was thus sent to server
		var field = this.selectorToField[event.currentTarget.id];
		var currentVal = this.model.get(field);
		var newVal = $(event.currentTarget).val();
		if (currentVal != newVal) {
			this.clearValidationErrors();
			this.model.save(field, newVal, { error : CMS.ServerError});
			return true;
		}
		else return false;
	}
});

CMS.Views.Settings.Main = Backbone.View.extend({
	// Model class is CMS.Models.Settings.CourseSettings
	// allow navigation between the tabs
	events: {
		'click .settings-page-menu a': "showSettingsTab",
		'mouseover #timezone' : "updateTime"
	},
	
	currentTab: null, 
	subviews: {},	// indexed by tab name

	initialize: function() {
		// load templates
		this.currentTab = this.$el.find('.settings-page-menu .is-shown').attr('data-section');
		// create the initial subview
		this.subviews[this.currentTab] = this.createSubview();
			
		// fill in fields
		this.$el.find("#course-name").val(this.model.get('courseLocation').get('name'));
		this.$el.find("#course-organization").val(this.model.get('courseLocation').get('org'));
		this.$el.find("#course-number").val(this.model.get('courseLocation').get('course'));
		this.$el.find('.set-date').datepicker({ 'dateFormat': 'm/d/yy' });
		this.$el.find(":input, textarea").focus(function() {
	      $("label[for='" + this.id + "']").addClass("is-focused");
	    }).blur(function() {
	      $("label").removeClass("is-focused");
	    });
		this.render();
	},
	
	render: function() {
		
		// create any necessary subviews and put them onto the page
		if (!this.model.has(this.currentTab)) {
			// TODO disable screen until fetch completes?
			var cachethis = this;
			this.model.retrieve(this.currentTab, function() {
				cachethis.subviews[cachethis.currentTab] = cachethis.createSubview();
				cachethis.subviews[cachethis.currentTab].render();
			});
			}
		else this.subviews[this.currentTab].render();
		
		var dateIntrospect = new Date();
		this.$el.find('#timezone').html("(" + dateIntrospect.getTimezone() + ")");
		
		return this;
	},
	
	createSubview: function() {
		switch (this.currentTab) {
		case 'details':
			return new CMS.Views.Settings.Details({
				el: this.$el.find('.settings-' + this.currentTab),
				model: this.model.get(this.currentTab)
			});
		case 'faculty':
			break;
		case 'grading':
			return new CMS.Views.Settings.Grading({
				el: this.$el.find('.settings-' + this.currentTab),
				model: this.model.get(this.currentTab)
			});
		case 'problems':
			break;
		case 'discussions':
			break;
		}
	},
	
	updateTime : function(e) {
		var now = new Date();
		var hours = now.getHours();
		var minutes = now.getMinutes();
		$(e.currentTarget).attr('title', (hours % 12 === 0 ? 12 : hours % 12) + ":" + (minutes < 10 ? "0" : "")  +
				now.getMinutes() + (hours < 12 ? "am" : "pm") + " (current local time)");
	},
	
	showSettingsTab: function(e) {
		this.currentTab = $(e.target).attr('data-section');
		$('.settings-page-section > section').hide();
		$('.settings-' + this.currentTab).show();
		$('.settings-page-menu .is-shown').removeClass('is-shown');
		$(e.target).addClass('is-shown');
		// fetch model for the tab if not loaded already
		this.render();
	}

});

CMS.Views.Settings.Details = CMS.Views.ValidatingView.extend({
	// Model class is CMS.Models.Settings.CourseDetails
	events : {
		"blur input" : "updateModel",
		"blur textarea" : "updateModel",
		'click .remove-course-syllabus' : "removeSyllabus",
		'click .new-course-syllabus' : 'assetSyllabus',
		'click .remove-course-introduction-video' : "removeVideo",
		'focus #course-overview' : "codeMirrorize"
	},
	initialize : function() {
		// TODO move the html frag to a loaded asset
		this.fileAnchorTemplate = _.template('<a href="<%= fullpath %>"> <i class="ss-icon ss-standard">&#x1F4C4;</i><%= filename %></a>');
		this.model.on('error', this.handleValidationError, this);
		this.selectorToField = _.invert(this.fieldToSelectorMap);
	},
	
	render: function() {
		this.setupDatePicker('start_date');
		this.setupDatePicker('end_date');
		this.setupDatePicker('enrollment_start');
		this.setupDatePicker('enrollment_end');
		
		if (this.model.has('syllabus')) {
			this.$el.find(this.fieldToSelectorMap['syllabus']).html(
					this.fileAnchorTemplate({
						fullpath : this.model.get('syllabus'),
						filename: 'syllabus'}));
			this.$el.find('.remove-course-syllabus').show();
		}
		else {
			this.$el.find('#' + this.fieldToSelectorMap['syllabus']).html("");
			this.$el.find('.remove-course-syllabus').hide();
		}
		
		this.$el.find('#' + this.fieldToSelectorMap['overview']).val(this.model.get('overview'));
		this.codeMirrorize(null, $('#course-overview')[0]);
		
		this.$el.find('.current-course-introduction-video iframe').attr('src', this.model.videosourceSample());
		if (this.model.has('intro_video')) {
			this.$el.find('.remove-course-introduction-video').show();
			this.$el.find('#' + this.fieldToSelectorMap['intro_video']).val(this.model.get('intro_video'));
		}
		else this.$el.find('.remove-course-introduction-video').hide();
		
		this.$el.find('#' + this.fieldToSelectorMap['effort']).val(this.model.get('effort'));
		
		return this;
	},
	fieldToSelectorMap : {
		'start_date' : "course-start",
		'end_date' : 'course-end',
		'enrollment_start' : 'enrollment-start',
		'enrollment_end' : 'enrollment-end',
		'syllabus' : '.current-course-syllabus .doc-filename',
		'overview' : 'course-overview',
		'intro_video' : 'course-introduction-video',
		'effort' : "course-effort"
	},

    setupDatePicker: function (fieldName) {
        var cacheModel = this.model;
        var div = this.$el.find('#' + this.fieldToSelectorMap[fieldName]);
        var datefield = $(div).find(".date");
        var timefield = $(div).find(".time");
        var cachethis = this;
        var savefield = function () {
            cachethis.clearValidationErrors();
            var date = datefield.datepicker('getDate');
            if (date) {
                var time = timefield.timepicker("getSecondsFromMidnight");
                if (!time) {
                    time = 0;
                }
                var newVal = new Date(date.getTime() + time * 1000);
                if (cacheModel.get(fieldName).getTime() !== newVal.getTime()) {
                    cacheModel.save(fieldName, newVal, { error: CMS.ServerError});
                }
            }
        };

        // instrument as date and time pickers
        timefield.timepicker();
        datefield.datepicker();

        // Using the change event causes savefield to be triggered twice, but it is necessary
        // to pick up when the date is typed directly in the field.
        datefield.change(savefield);
        timefield.on('changeTime', savefield);

        datefield.datepicker('setDate', this.model.get(fieldName));
        if (this.model.has(fieldName)) timefield.timepicker('setTime', this.model.get(fieldName));
    },
	
	updateModel: function(event) {
		switch (event.currentTarget.id) {
		case 'course-start-date': // handled via onSelect method
		case 'course-end-date':
		case 'course-enrollment-start-date':
		case 'course-enrollment-end-date':
			break;

		case 'course-overview':
			// handled via code mirror
			break;

		case 'course-effort':
			this.saveIfChanged(event);
			break;
		case 'course-introduction-video':
			this.clearValidationErrors();
			var previewsource = this.model.save_videosource($(event.currentTarget).val());
			this.$el.find(".current-course-introduction-video iframe").attr("src", previewsource);
			if (this.model.has('intro_video')) {
				this.$el.find('.remove-course-introduction-video').show();
			}
			else {
				this.$el.find('.remove-course-introduction-video').hide();
			}
			break;
			
		default:
			break;
		}
		
	},
	
	removeSyllabus: function() {
		if (this.model.has('syllabus'))	this.model.save({'syllabus': null}, 
				{ error : CMS.ServerError});
	},
	
	assetSyllabus : function() {
		// TODO implement
	},
	
	removeVideo: function() {
		if (this.model.has('intro_video')) {
			this.model.save_videosource(null);
			this.$el.find(".current-course-introduction-video iframe").attr("src", "");
			this.$el.find('#' + this.fieldToSelectorMap['intro_video']).val("");
			this.$el.find('.remove-course-introduction-video').hide();
		}
	},
	codeMirrors : {},
    codeMirrorize: function (e, forcedTarget) {
        var thisTarget;
        if (forcedTarget) {
            thisTarget = forcedTarget;
            thisTarget.id = $(thisTarget).attr('id');
        } else {
            thisTarget = e.currentTarget;
        }

        if (!this.codeMirrors[thisTarget.id]) {
            var cachethis = this;
            var field = this.selectorToField[thisTarget.id];
            this.codeMirrors[thisTarget.id] = CodeMirror.fromTextArea(thisTarget, {
                mode: "text/html", lineNumbers: true, lineWrapping: true,
                onBlur: function (mirror) {
                    mirror.save();
                    cachethis.clearValidationErrors();
                    var newVal = mirror.getValue();
                    if (cachethis.model.get(field) != newVal) cachethis.model.save(field, newVal,
                        { error: CMS.ServerError});
                }
            });
        }
    }
	
});

CMS.Views.Settings.Grading = CMS.Views.ValidatingView.extend({
	// Model class is CMS.Models.Settings.CourseGradingPolicy
	events : {
		"blur input" : "updateModel",
		"blur textarea" : "updateModel",
		"blur span[contenteditable=true]" : "updateDesignation",
		"click .settings-extra header" : "showSettingsExtras",
		"click .new-grade-button" : "addNewGrade",
		"click .remove-button" : "removeGrade",
		"click .add-grading-data" : "addAssignmentType"
	},
	initialize : function() {
		//  load template for grading view
    	var self = this;
        this.gradeCutoffTemplate = _.template('<li class="grade-specific-bar" style="width:<%= width %>%"><span class="letter-grade" contenteditable>' +
        		'<%= descriptor %>' +
        		'</span><span class="range"></span>' +
        		'<% if (removable) {%><a href="#" class="remove-button">remove</a><% ;} %>' +
        		'</li>');

        // Instrument grading scale
        // convert cutoffs to inversely ordered list
        var modelCutoffs = this.model.get('grade_cutoffs');
        for (var cutoff in modelCutoffs) {
        	this.descendingCutoffs.push({designation: cutoff, cutoff: Math.round(modelCutoffs[cutoff] * 100)});
        }
        this.descendingCutoffs = _.sortBy(this.descendingCutoffs,
        		function (gradeEle) { return -gradeEle['cutoff']; });

        // Instrument grace period
        this.$el.find('#course-grading-graceperiod').timepicker();

        // instantiates an editor template for each update in the collection
        // Because this calls render, put it after everything which render may depend upon to prevent race condition.
        window.templateLoader.loadRemoteTemplate("course_grade_policy",
        		"/static/client_templates/course_grade_policy.html",
        		function (raw_template) {
        	self.template = _.template(raw_template);
        	self.render();
        }
        );
		this.model.on('error', this.handleValidationError, this);
		this.model.get('graders').on('remove', this.render, this);
		this.model.get('graders').on('reset', this.render, this);
		this.model.get('graders').on('add', this.render, this);
		this.selectorToField = _.invert(this.fieldToSelectorMap);
	},
	
	render: function() {
		// prevent bootstrap race condition by event dispatch
		if (!this.template) return;
		
		// Create and render the grading type subs
		var self = this;
		var gradelist = this.$el.find('.course-grading-assignment-list');
		// Undo the double invocation error. At some point, fix the double invocation
		$(gradelist).empty();
		var gradeCollection = this.model.get('graders');
		gradeCollection.each(function(gradeModel) {
			$(gradelist).append(self.template({model : gradeModel }));
			var newEle = gradelist.children().last();
			var newView = new CMS.Views.Settings.GraderView({el: newEle, 
				model : gradeModel, collection : gradeCollection });
		});
		
		// render the grade cutoffs
		this.renderCutoffBar();
		
		var graceEle = this.$el.find('#course-grading-graceperiod');
		graceEle.timepicker({'timeFormat' : 'H:i'}); // init doesn't take setTime
		if (this.model.has('grace_period')) graceEle.timepicker('setTime', this.model.gracePeriodToDate());
		// remove any existing listeners to keep them from piling on b/c render gets called frequently
		graceEle.off('change', this.setGracePeriod);
		graceEle.on('change', this, this.setGracePeriod);
		
		return this;
	},
	addAssignmentType : function(e) {
		e.preventDefault();
		this.model.get('graders').push({});
	},
	fieldToSelectorMap : {
		'grace_period' : 'course-grading-graceperiod'
	},
	setGracePeriod : function(event) {
		event.data.clearValidationErrors();
		var newVal = event.data.model.dateToGracePeriod($(event.currentTarget).timepicker('getTime'));
		if (event.data.model.get('grace_period') != newVal) event.data.model.save('grace_period', newVal,
				{ error : CMS.ServerError});
	},
	updateModel : function(event) {
		if (!this.selectorToField[event.currentTarget.id]) return;

		switch (this.selectorToField[event.currentTarget.id]) {
		case 'grace_period': // handled above
			break;

		default:
			this.saveIfChanged(event);
			break;
		}
	},
	
	// Grade sliders attributes and methods
	// Grade bars are li's ordered A -> F with A taking whole width, B overlaying it with its paint, ...
	// The actual cutoff for each grade is the width % of the next lower grade; so, the hack here
	// is to lay down a whole width bar claiming it's A and then lay down bars for each actual grade
	// starting w/ A but posting the label in the preceding li and setting the label of the last to "Fail" or "F"
	
	// A does not have a drag bar (cannot change its upper limit)
	// Need to insert new bars in right place.
	GRADES : ['A', 'B', 'C', 'D'],	// defaults for new grade designators
	descendingCutoffs : [],  // array of { designation : , cutoff : }
	gradeBarWidth : null, // cache of value since it won't change (more certain)
	
	renderCutoffBar: function() {
		var gradeBar =this.$el.find('.grade-bar'); 
		this.gradeBarWidth = gradeBar.width();
		var gradelist = gradeBar.children('.grades');
		// HACK fixing a duplicate call issue by undoing previous call effect. Need to figure out why called 2x
		gradelist.empty();
		var nextWidth = 100; // first width is 100%
        // Can probably be simplified to one variable now.
        var removable = false;
        var draggable = false; // first and last are not removable, first is not draggable
		_.each(this.descendingCutoffs, 
				function(cutoff, index) {
			var newBar = this.gradeCutoffTemplate({ 
				descriptor : cutoff['designation'] , 
				width : nextWidth, 
				removable : removable });
			gradelist.append(newBar);
			if (draggable) {
				newBar = gradelist.children().last(); // get the dom object not the unparsed string
				newBar.resizable({
					handles: "e",
					containment : "parent",
					start : this.startMoveClosure(),
					resize : this.moveBarClosure(),
					stop : this.stopDragClosure()
				});
			}
			// prepare for next
			nextWidth = cutoff['cutoff'];
			removable = true; // first is not removable, all others are
			draggable = true;
		},
		this);
		// add fail which is not in data
		var failBar = this.gradeCutoffTemplate({ descriptor : this.failLabel(), 
			width : nextWidth, removable : false});
		$(failBar).find("span[contenteditable=true]").attr("contenteditable", false);
		gradelist.append(failBar);
		gradelist.children().last().resizable({
			handles: "e",
			containment : "parent",
			start : this.startMoveClosure(),
			resize : this.moveBarClosure(),
			stop : this.stopDragClosure()
		});
		
		this.renderGradeRanges();
	},
	
	showSettingsExtras : function(event) {
		$(event.currentTarget).toggleClass('active');
		$(event.currentTarget).siblings.toggleClass('is-shown');
	},
	

	startMoveClosure : function() {
		// set min/max widths
		var cachethis = this;
		var widthPerPoint = cachethis.gradeBarWidth / 100;
		return function(event, ui) {
			var barIndex = ui.element.index();
			// min and max represent limits not labels (note, can's make smaller than 3 points wide)
			var min = (barIndex < cachethis.descendingCutoffs.length ? cachethis.descendingCutoffs[barIndex]['cutoff'] + 3 : 3);
			// minus 2 b/c minus 1 is the element we're effecting. It's max is just shy of the next one above it
			var max = (barIndex >= 2 ? cachethis.descendingCutoffs[barIndex - 2]['cutoff'] - 3 : 97);
			ui.element.resizable("option",{minWidth : min * widthPerPoint, maxWidth : max * widthPerPoint});
		};
	},

	moveBarClosure : function() {
		// 0th ele doesn't have a bar; so, will never invoke this
		var cachethis = this;
		return function(event, ui) {
			var barIndex = ui.element.index();
			// min and max represent limits not labels (note, can's make smaller than 3 points wide)
			var min = (barIndex < cachethis.descendingCutoffs.length ? cachethis.descendingCutoffs[barIndex]['cutoff'] + 3 : 3);
			// minus 2 b/c minus 1 is the element we're effecting. It's max is just shy of the next one above it
			var max = (barIndex >= 2 ? cachethis.descendingCutoffs[barIndex - 2]['cutoff'] - 3 : 100);
			var percentage = Math.min(Math.max(ui.size.width / cachethis.gradeBarWidth * 100, min), max);
			cachethis.descendingCutoffs[barIndex - 1]['cutoff'] = Math.round(percentage);
			cachethis.renderGradeRanges();
		};
	},
	
	renderGradeRanges: function() {
		// the labels showing the range e.g., 71-80
		var cutoffs = this.descendingCutoffs;
		this.$el.find('.range').each(function(i) {
			var min = (i < cutoffs.length ? cutoffs[i]['cutoff'] : 0);
			var max = (i > 0 ? cutoffs[i - 1]['cutoff'] : 100);
			$(this).text(min + '-' + max);
		});
	},
	
	stopDragClosure: function() {
		var cachethis = this;
		return function(event, ui) {
			// for some reason the resize is setting height to 0
			cachethis.saveCutoffs();
		};
	},
	
	saveCutoffs: function() {
		this.model.save('grade_cutoffs', 
				_.reduce(this.descendingCutoffs, 
						function(object, cutoff) { 
					object[cutoff['designation']] = cutoff['cutoff'] / 100.0;
					return object;
				}, 
				{}),
				{ error : CMS.ServerError});
	},
	
	addNewGrade: function(e) {
		e.preventDefault();
		var gradeLength = this.descendingCutoffs.length; // cutoffs doesn't include fail/f so this is only the passing grades
		if(gradeLength > 3) {
			// TODO shouldn't we disable the button
			return;
		}
		var failBarWidth = this.descendingCutoffs[gradeLength - 1]['cutoff'];
		// going to split the grade above the insertion point in half leaving fail in same place
		var nextGradeTop = (gradeLength > 1 ? this.descendingCutoffs[gradeLength - 2]['cutoff'] : 100);
		var targetWidth = failBarWidth + ((nextGradeTop - failBarWidth) / 2);
		this.descendingCutoffs.push({designation: this.GRADES[gradeLength], cutoff: failBarWidth});
		this.descendingCutoffs[gradeLength - 1]['cutoff'] = Math.round(targetWidth);
		
		var $newGradeBar = this.gradeCutoffTemplate({ descriptor : this.GRADES[gradeLength], 
			width : targetWidth, removable : true });
		var gradeDom = this.$el.find('.grades');
		gradeDom.children().last().before($newGradeBar);
		var newEle = gradeDom.children()[gradeLength];
		$(newEle).resizable({
			handles: "e",
			containment : "parent",
			start : this.startMoveClosure(),
			resize : this.moveBarClosure(),
			stop : this.stopDragClosure()
		});
		
		// Munge existing grade labels?
		// If going from Pass/Fail to 3 levels, change to Pass to A
		if (gradeLength === 1 && this.descendingCutoffs[0]['designation'] === 'Pass') {
			this.descendingCutoffs[0]['designation'] = this.GRADES[0];
			this.setTopGradeLabel();
		}
		this.setFailLabel();
			
		this.renderGradeRanges();
		this.saveCutoffs();
	},
	
	removeGrade: function(e) {
		e.preventDefault();
		var domElement = $(e.currentTarget).closest('li');
		var index = domElement.index();
		// copy the boundary up to the next higher grade then remove
		this.descendingCutoffs[index - 1]['cutoff'] = this.descendingCutoffs[index]['cutoff'];
		this.descendingCutoffs.splice(index, 1);
		domElement.remove();
		
		if (this.descendingCutoffs.length === 1 && this.descendingCutoffs[0]['designation'] === this.GRADES[0]) {
			this.descendingCutoffs[0]['designation'] = 'Pass';
			this.setTopGradeLabel();
		}
		this.setFailLabel();
		this.renderGradeRanges();
		this.saveCutoffs();
	},
	
	updateDesignation: function(e) {
		var index = $(e.currentTarget).closest('li').index();
		this.descendingCutoffs[index]['designation'] = $(e.currentTarget).html();
		this.saveCutoffs();
	},

	failLabel: function() {
		if (this.descendingCutoffs.length === 1) return 'Fail';
		else return 'F';
	},
	setFailLabel: function() {
		this.$el.find('.grades .letter-grade').last().html(this.failLabel());
	},
	setTopGradeLabel: function() {
		this.$el.find('.grades .letter-grade').first().html(this.descendingCutoffs[0]['designation']);
	}

});

CMS.Views.Settings.GraderView = CMS.Views.ValidatingView.extend({
	// Model class is CMS.Models.Settings.CourseGrader
	events : {
		"blur input" : "updateModel",
		"blur textarea" : "updateModel",
		"click .remove-grading-data" : "deleteModel"
	},
	initialize : function() {
		this.model.on('error', this.handleValidationError, this);
		this.selectorToField = _.invert(this.fieldToSelectorMap);
		this.render();
	},
	
	render: function() {
		return this;
	},
	fieldToSelectorMap : {
		'type' : 'course-grading-assignment-name',
		'short_label' : 'course-grading-assignment-shortname',
		'min_count' : 'course-grading-assignment-totalassignments',
		'drop_count' : 'course-grading-assignment-droppable',
		'weight' : 'course-grading-assignment-gradeweight'
	},
	updateModel : function(event) {
		// HACK to fix model sometimes losing its pointer to the collection [I think I fixed this but leaving
		// this in out of paranoia. If this error ever happens, the user will get a warning that they cannot
		// give 2 assignments the same name.]
		if (!this.model.collection) {
			this.model.collection = this.collection;
		}
		
		switch (event.currentTarget.id) {
		case 'course-grading-assignment-totalassignments':
			this.$el.find('#course-grading-assignment-droppable').attr('max', $(event.currentTarget).val());
			this.saveIfChanged(event);
			break;
		case 'course-grading-assignment-name':
			var oldName = this.model.get('type');
			if (this.saveIfChanged(event) && !_.isEmpty(oldName)) {
				// overload the error display logic
				this._cacheValidationErrors.push(event.currentTarget);
				$(event.currentTarget).parent().append(
						this.errorTemplate({message : 'For grading to work, you must change all "' + oldName +
							'" subsections to "' + this.model.get('type') + '".'}));
			}
			break;
		default:
			this.saveIfChanged(event);
			break;
		}
	},
	deleteModel : function(e) {
		this.model.destroy(
				{ error : CMS.ServerError});
		e.preventDefault();
	}
	
});