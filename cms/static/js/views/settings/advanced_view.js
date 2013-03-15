if (!CMS.Views['Settings']) CMS.Views.Settings = {};

CMS.Views.Settings.Advanced = CMS.Views.ValidatingView.extend({
    error_saving : "error_saving",
    successful_changes: "successful_changes",

    // Model class is CMS.Models.Settings.Advanced
    events : {
        'focus :input' : "focusInput",
        'blur :input' : "blurInput"
        // TODO enable/disable save based on validation (currently enabled whenever there are changes)
    },
    initialize : function() {
        var self = this;
        // instantiates an editor template for each update in the collection
        window.templateLoader.loadRemoteTemplate("advanced_entry",
            "/static/client_templates/advanced_entry.html",
            function (raw_template) {
                self.template = _.template(raw_template);
                self.render();
            }
        );
        // because these are outside of this.$el, they can't be in the event hash
        $('.save-button').on('click', this, this.saveView);
        $('.cancel-button').on('click', this, this.revertView);
        this.listenTo(this.model, 'error', CMS.ServerError);
        this.listenTo(this.model, 'invalid', this.handleValidationError);
    },
    render: function() {
        // catch potential outside call before template loaded
        if (!this.template) return this;

        var listEle$ = this.$el.find('.course-advanced-policy-list');
        listEle$.empty();
        
        // b/c we've deleted all old fields, clear the map and repopulate
        this.fieldToSelectorMap = {};
        this.selectorToField = {};

        // iterate through model and produce key : value editors for each property in model.get
        var self = this;
        _.each(_.sortBy(_.keys(this.model.attributes), _.identity),
            function(key) {
                listEle$.append(self.renderTemplate(key, self.model.get(key)));
            });

        var policyValues = listEle$.find('.json');
        _.each(policyValues, this.attachJSONEditor, this);
        this.showMessage();
        return this;
    },
    attachJSONEditor : function (textarea) {
        // Since we are allowing duplicate keys at the moment, it is possible that we will try to attach
        // JSON Editor to a value that already has one. Therefore only attach if no CodeMirror peer exists.
        if ( $(textarea).siblings().hasClass('CodeMirror')) {
            return;
        }

        var self = this;
        var oldValue = $(textarea).val();
        CodeMirror.fromTextArea(textarea, {
            mode: "application/json", lineNumbers: false, lineWrapping: false,
            onChange: function(instance, changeobj) {
                // this event's being called even when there's no change :-(
                if (instance.getValue() !== oldValue) self.showSaveCancelButtons();
            },
            onFocus : function(mirror) {
              $(textarea).parent().children('label').addClass("is-focused");
            },
            onBlur: function (mirror) {
                $(textarea).parent().children('label').removeClass("is-focused");
                var key = $(mirror.getWrapperElement()).closest('.field-group').children('.key').attr('id');
                var stringValue = $.trim(mirror.getValue());
                // update CodeMirror to show the trimmed value.
                mirror.setValue(stringValue);
                var JSONValue = undefined;
                try {
                    JSONValue = JSON.parse(stringValue);
                } catch (e) {
                    // If it didn't parse, try converting non-arrays/non-objects to a String.
                    // But don't convert single-quote strings, which are most likely errors.
                    var firstNonWhite = stringValue.substring(0, 1);
                    if (firstNonWhite !== "{" && firstNonWhite !== "[" && firstNonWhite !== "'") {
                        try {
                            stringValue = '"'+stringValue +'"';
                            JSONValue = JSON.parse(stringValue);
                            mirror.setValue(stringValue);
                        } catch(quotedE) {
                            // TODO: validation error
                            // console.log("Error with JSON, even after converting to String.");
                            // console.log(quotedE);
                            JSONValue = undefined;
                        }
                    }
                }
                if (JSONValue !== undefined) {
                    self.clearValidationErrors();
                    self.model.set(key, JSONValue, {validate: true});
                }
            }
        });
    },
    showMessage: function (type) {
        this.$el.find(".message-status").removeClass("is-shown");
        if (type) {
            if (type === this.error_saving) {
                this.$el.find(".message-status.error").addClass("is-shown");
            }
            else if (type === this.successful_changes) {
                this.$el.find(".message-status.confirm").addClass("is-shown");
                this.hideSaveCancelButtons();
            }
        }
        else {
            // This is the case of the page first rendering, or when Cancel is pressed.
            this.hideSaveCancelButtons();
        }
    },
    showSaveCancelButtons: function(event) {
        if (!this.buttonsVisible) {
            this.$el.find(".message-status").removeClass("is-shown");
            $('.wrapper-notification').addClass('is-shown');
            this.buttonsVisible = true;
        }
    },
    hideSaveCancelButtons: function() {
        $('.wrapper-notification').removeClass('is-shown');
        this.buttonsVisible = false;
    },
    saveView : function(event) {
        // TODO one last verification scan:
        //    call validateKey on each to ensure proper format
        //    check for dupes
        var self = event.data;
        self.model.save({},
            {
            success : function() {
                self.render();
                self.showMessage(self.successful_changes);
            },
            error : CMS.ServerError
        });
    },
    revertView : function(event) {
        var self = event.data;
        self.model.deleteKeys = [];
        self.model.clear({silent : true});
        self.model.fetch({
            success : function() { self.render(); },
            error : CMS.ServerError
        });
    },
    renderTemplate: function (key, value) {
        var newKeyId = _.uniqueId('policy_key_'),
        newEle = this.template({ key : key, value : JSON.stringify(value, null, 4),
            keyUniqueId: newKeyId, valueUniqueId: _.uniqueId('policy_value_')});
        
        this.fieldToSelectorMap[key] = newKeyId;
        this.selectorToField[newKeyId] = key;
        return newEle;
    },
    focusInput : function(event) {
        $(event.target).prev().addClass("is-focused");
    },
    blurInput : function(event) {
        $(event.target).prev().removeClass("is-focused");
    }
});