/*  this view should own everything on the page which has controls effecting its operation
   generate other views for the individual editors.
   The render here adds views for each update/handout by delegating to their collections but does not
   generate any html for the surrounding page.
*/
CMS.Views.CourseInfoEdit = Backbone.View.extend({
  // takes CMS.Models.CourseInfo as model
  tagName: 'div',

  render: function() {
    // instantiate the ClassInfoUpdateView and delegate the proper dom to it
    new CMS.Views.ClassInfoUpdateView({
        el: this.$('#course-update-view'),
        collection: this.model.get('updates')
    });
    // TODO instantiate the handouts view
    return this;
  }
});

// ??? Programming style question: should each of these classes be in separate files?
CMS.Views.ClassInfoUpdateView = Backbone.View.extend({
    // collection is CourseUpdateCollection
    events: {
        "click .new-update-button" : "onNew",
        "click .save-button" : "onSave",
        "click .cancel-button" : "onCancel",
        "click .edit-button" : "onEdit",
        "click .delete-button" : "onDelete"
    },
        
    initialize: function() {
    	var self = this;
        // instantiates an editor template for each update in the collection
        window.templateLoader.loadRemoteTemplate("course_info_update",
        	// TODO Where should the template reside? how to use the static.url to create the path?
            "/static/coffee/src/client_templates/course_info_update.html",
            function (raw_template) { 
        		self.template = _.template(raw_template);
        		self.render();
        }
        );
    },
        
    render: function () {
          // iterate over updates and create views for each using the template
          var updateEle = this.$el.find("#course-update-list");
          // remove and then add all children
          $(updateEle).empty();
          var self = this;
          this.collection.each(function (update) {
        	  var newEle = self.template({ updateModel : update });
              $(updateEle).append(newEle);
          });
          this.$el.find(".new-update-form").hide();
          return this;
    },
    
    onNew: function(event) {
        // create new obj, insert into collection, and render this one ele overriding the hidden attr
        var newModel = new CMS.Models.CourseUpdate();
        this.collection.add(newModel, {at : 0});
        
        var newForm = this.template({ updateModel : newModel });
        var updateEle = this.$el.find("#course-update-list");
        $(updateEle).append(newForm);
        $(newForm).find(".new-update-form").show();
    },
    
    onSave: function(event) {
        var targetModel = this.eventModel(event);
        targetModel.set({ date : this.dateEntry(event).val(), content : this.contentEntry(event).val() });
        // push change to display, hide the editor, submit the change
        $(this.dateDisplay(event)).val(targetModel.get('date'));
        $(this.contentDisplay(event)).val(targetModel.get('content'));
        $(this.editor(event)).hide();
        
        targetModel.save();
    },
    
    onCancel: function(event) {
        // change editor contents back to model values and hide the editor
        $(this.editor(event)).hide();
        var targetModel = this.eventModel(event);
        $(this.dateEntry(event)).val(targetModel.get('date'));
        $(this.contentEntry(event)).val(targetModel.get('content'));
    },
    
    onEdit: function(event) {
        $(this.editor(event)).show();
    },
        
    onDelete: function(event) {
        // TODO ask for confirmation
        // remove the dom element and delete the model
        var targetModel = this.eventModel(event);
        this.modelDom(event).remove();
        var cacheThis = this;
        targetModel.destroy({success : function (model, response) { 
            cacheThis.collection.fetch({success : function() {cacheThis.render();}});
        }
        });
    },
    
    // Dereferencing from events to screen elements    
    eventModel: function(event) {
        // not sure if it should be currentTarget or delegateTarget
        return this.collection.getByCid($(event.currentTarget).attr("name"));
    },
        
    modelDom: function(event) {
        return $(event.currentTarget).closest("li");
    },
            
    editor: function(event) {
    	var li = $(event.currentTarget).closest("li");
    	if (li) return $(li).find("form").first();
    },

    dateEntry: function(event) {
    	var li = $(event.currentTarget).closest("li");
    	if (li) return $(li).find("#date-entry").first();
    },

    contentEntry: function(event) {
        return $(event.currentTarget).closest("li").find(".new-update-content").first();
    },
        
    dateDisplay: function(event) {
        return $(event.currentTarget).closest("li").find("#date-display").first();
    },

    contentDisplay: function(event) {
        return $(event.currentTarget).closest("li").find(".update-contents").first();
    }
        
});
        