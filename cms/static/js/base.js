var $body;
var $modal;
var $modalCover;
var $newComponentItem;
var $changedInput;
var $spinner;

$(document).ready(function() {
  $body = $('body');
  $modal = $('.history-modal');
  $modalCover = $('<div class="modal-cover">');
  // cdodge: this looks funny, but on AWS instances, this base.js get's wrapped in a separate scope as part of Django static
  // pipelining (note, this doesn't happen on local runtimes). So if we set it on window, when we can access it from other
  // scopes (namely the course-info tab)
  window.$modalCover = $modalCover;
  
  // Control whether template caching in local memory occurs (see template_loader.js). Caching screws up development but may
  // be a good optimization in production (it works fairly well)
  window.cachetemplates = false;

  $body.append($modalCover);
  $newComponentItem = $('.new-component-item');
  $newComponentTypePicker = $('.new-component');
  $newComponentTemplatePickers = $('.new-component-templates');
  $newComponentButton = $('.new-component-button');
  $spinner = $('<span class="spinner-in-field-icon"></span>');
  $body.bind('keyup', onKeyUp);

  $('.expand-collapse-icon').bind('click', toggleSubmodules);
  $('.visibility-options').bind('change', setVisibility);

  $modal.bind('click', hideModal);
  $modalCover.bind('click', hideModal);
  $('.uploads .upload-button').bind('click', showUploadModal);
  $('.upload-modal .close-button').bind('click', hideModal);

  $body.on('click', '.embeddable-xml-input', function(){ $(this).select(); });

  $('.unit .item-actions .delete-button').bind('click', deleteUnit);
  $('.new-unit-item').bind('click', createNewUnit);

  $('body').addClass('js');

  // lean/simple modal
  $('a[rel*=modal]').leanModal({overlay : 0.80, closeButton: '.action-modal-close' });
  $('a.action-modal-close').click(function(e){
    (e).preventDefault();
  });

  // nav - dropdown related
  $body.click(function(e){
    $('.nav-dropdown .nav-item .wrapper-nav-sub').removeClass('is-shown');
    $('.nav-dropdown .nav-item .title').removeClass('is-selected');
  });

  $('.nav-dropdown .nav-item .title').click(function(e){

    $subnav = $(this).parent().find('.wrapper-nav-sub');
    $title = $(this).parent().find('.title');
    e.preventDefault();
    e.stopPropagation();

    if ($subnav.hasClass('is-shown')) {
      $subnav.removeClass('is-shown');
      $title.removeClass('is-selected');
    }

    else {
      $('.nav-dropdown .nav-item .title').removeClass('is-selected');
      $('.nav-dropdown .nav-item .wrapper-nav-sub').removeClass('is-shown');
      $title.addClass('is-selected');
      $subnav.addClass('is-shown');
    }
  });

  // general link management - new window/tab
  $('a[rel="external"]').attr('title','This link will open in a new browser window/tab').click(function(e) {
    window.open($(this).attr('href'));
    e.preventDefault();
  });

  // general link management - lean modal window
  $('a[rel="modal"]').attr('title','This link will open in a modal window').leanModal({overlay : 0.50, closeButton: '.action-modal-close' });
  $('.action-modal-close').click(function(e){
    (e).preventDefault();
  });

  // toggling overview section details
  $(function(){
    if($('.courseware-section').length > 0) {
    $('.toggle-button-sections').addClass('is-shown');
    }
  });
  $('.toggle-button-sections').bind('click', toggleSections);

  // autosave when a field is updated on the subsection page
  $body.on('keyup', '.subsection-display-name-input, .unit-subtitle, .policy-list-value', checkForNewValue);
  $('.subsection-display-name-input, .unit-subtitle, .policy-list-name, .policy-list-value').each(function(i) {
    this.val = $(this).val();
  });
  $("#start_date, #start_time, #due_date, #due_time").bind('change', autosaveInput);
  $('.sync-date, .remove-date').bind('click', autosaveInput);

  // expand/collapse methods for optional date setters
  $('.set-date').bind('click', showDateSetter);
  $('.remove-date').bind('click', removeDateSetter);
  // add new/delete section
  $('.new-courseware-section-button').bind('click', addNewSection);
  $('.delete-section-button').bind('click', deleteSection);
  
  // add new/delete subsection
  $('.new-subsection-item').bind('click', addNewSubsection);
  $('.delete-subsection-button').bind('click', deleteSubsection);
  // add/remove policy metadata button click handlers
  $('.add-policy-data').bind('click', addPolicyMetadata);
  $('.remove-policy-data').bind('click', removePolicyMetadata);
  $body.on('click', '.policy-list-element .save-button', savePolicyMetadata);
  $body.on('click', '.policy-list-element .cancel-button', cancelPolicyMetadata);

  $('.sync-date').bind('click', syncReleaseDate);

  // import form setup
  $('.import .file-input').bind('change', showImportSubmit);
  $('.import .choose-file-button, .import .choose-file-button-inline').bind('click', function(e) {
    e.preventDefault();
    $('.import .file-input').click();
  });

  $('.new-course-button').bind('click', addNewCourse);

  // section name editing
  $('.section-name').bind('click', editSectionName);
  $('.edit-section-name-cancel').bind('click', cancelEditSectionName);
  // $('.edit-section-name-save').bind('click', saveEditSectionName);

  // section date setting
  $('.set-publish-date').bind('click', setSectionScheduleDate);
  $('.edit-section-start-cancel').bind('click', cancelSetSectionScheduleDate);
  $('.edit-section-start-save').bind('click', saveSetSectionScheduleDate);

  $('.upload-modal .choose-file-button').bind('click', showFileSelectionMenu);

  $body.on('click', '.section-published-date .edit-button', editSectionPublishDate);
  $body.on('click', '.section-published-date .schedule-button', editSectionPublishDate);
  $body.on('click', '.edit-subsection-publish-settings .save-button', saveSetSectionScheduleDate);
  $body.on('click', '.edit-subsection-publish-settings .cancel-button', hideModal);
  $body.on('change', '.edit-subsection-publish-settings .start-date', function() {
    if($('.edit-subsection-publish-settings').find('.start-time').val() == '') {
      $('.edit-subsection-publish-settings').find('.start-time').val('12:00am');    
    }
  });
  $('.edit-subsection-publish-settings').on('change', '.start-date, .start-time', function() {
    $('.edit-subsection-publish-settings').find('.save-button').show();
  });
});

// function collapseAll(e) {
//     $('.branch').addClass('collapsed');
//     $('.expand-collapse-icon').removeClass('collapse').addClass('expand');
// }

function toggleSections(e) {
  e.preventDefault();

  $section = $('.courseware-section');
  sectionCount = $section.length;
  $button = $(this);
  $labelCollapsed = $('<i class="ss-icon ss-symbolicons-block">up</i> <span class="label">Collapse All Sections</span>');
  $labelExpanded = $('<i class="ss-icon ss-symbolicons-block">down</i> <span class="label">Expand All Sections</span>');

  var buttonLabel = $button.hasClass('is-activated') ? $labelCollapsed : $labelExpanded;
  $button.toggleClass('is-activated').html(buttonLabel);

  if($button.hasClass('is-activated')) {
    $section.addClass('collapsed');
    // first child in order to avoid the icons on the subsection lists which are not in the first child 
    $section.find('header .expand-collapse-icon').removeClass('collapse').addClass('expand');
  } else {
    $section.removeClass('collapsed');
    // first child in order to avoid the icons on the subsection lists which are not in the first child 
    $section.find('header .expand-collapse-icon').removeClass('expand').addClass('collapse');
  }
}

function editSectionPublishDate(e) {
  e.preventDefault();
  $modal = $('.edit-subsection-publish-settings').show();
  $modal = $('.edit-subsection-publish-settings').show();
  $modal.attr('data-id', $(this).attr('data-id'));
  $modal.find('.start-date').val($(this).attr('data-date'));
  $modal.find('.start-time').val($(this).attr('data-time'));
  if($modal.find('.start-date').val() == '' && $modal.find('.start-time').val() == '') {
    $modal.find('.save-button').hide();
  }    
  $modal.find('.section-name').html('"' + $(this).closest('.courseware-section').find('.section-name-span').text() + '"');
  $modalCover.show();
}

function showImportSubmit(e) {
  var filepath = $(this).val();
  if(filepath.substr(filepath.length - 6, 6) == 'tar.gz') {
    $('.error-block').hide();
    $('.file-name').html($(this).val().replace('C:\\fakepath\\', ''));
    $('.file-name-block').show();
    $('.import .choose-file-button').hide();
    $('.submit-button').show();
    $('.progress').show();
  } else {
    $('.error-block').html('File format not supported. Please upload a file with a <code>tar.gz</code> extension.').show();
  }
}

function syncReleaseDate(e) {
  e.preventDefault();
  $(this).closest('.notice').hide();
  $("#start_date").val("");
  $("#start_time").val("");
}

function addPolicyMetadata(e) {
  e.preventDefault();
  var template =$('#add-new-policy-element-template > li');
  var newNode = template.clone();
  var _parent_el = $(this).parent('ol:.policy-list');
  newNode.insertBefore('.add-policy-data');
  $('.remove-policy-data').bind('click', removePolicyMetadata);
  newNode.find('.policy-list-name').focus();
}

function savePolicyMetadata(e) {
  e.preventDefault();

  var $policyElement = $(this).parents('.policy-list-element');
  saveSubsection()
  $policyElement.removeClass('new-policy-list-element');
  $policyElement.find('.policy-list-name').attr('disabled', 'disabled');
  $policyElement.removeClass('editing');
}

function cancelPolicyMetadata(e) {
  e.preventDefault();

  var $policyElement = $(this).parents('.policy-list-element');
  if(!$policyElement.hasClass('editing')) {
    $policyElement.remove();
  } else {
    $policyElement.removeClass('new-policy-list-element');
    $policyElement.find('.policy-list-name').val($policyElement.data('currentValues')[0]);
    $policyElement.find('.policy-list-value').val($policyElement.data('currentValues')[1]);
  }
  $policyElement.removeClass('editing');
}

function removePolicyMetadata(e) {
  e.preventDefault();

  if(!confirm('Are you sure you wish to delete this item. It cannot be reversed!'))
     return;
   
  policy_name = $(this).data('policy-name');
  var _parent_el = $(this).parent('li:.policy-list-element');
  if ($(_parent_el).hasClass("new-policy-list-element")) {
    _parent_el.remove();        
  } else {
    _parent_el.appendTo("#policy-to-delete");
  }
  saveSubsection()
}

function getEdxTimeFromDateTimeVals(date_val, time_val, format) {
  var edxTimeStr = null;

  if (date_val != '') {
    if (time_val == '') 
      time_val = '00:00';

    // Note, we are using date.js utility which has better parsing abilities than the built in JS date parsing
    date = Date.parse(date_val + " " + time_val);
    if (format == null)
      format = 'yyyy-MM-ddTHH:mm';

    edxTimeStr = date.toString(format);
  }

  return edxTimeStr;
}

function getEdxTimeFromDateTimeInputs(date_id, time_id, format) {
  var input_date = $('#'+date_id).val();
  var input_time = $('#'+time_id).val();

  return getEdxTimeFromDateTimeVals(input_date, input_time, format);
}

function checkForNewValue(e) {
  if($(this).parents('.new-policy-list-element')[0]) {
    return;
  }

  if(this.val) {
    this.hasChanged = this.val != $(this).val();    
  } else {
    this.hasChanged = false;
  }

  this.val = $(this).val();
  if(this.hasChanged) {
    if(this.saveTimer) {
      clearTimeout(this.saveTimer);
    }

    this.saveTimer = setTimeout(function() {
      $changedInput = $(e.target);
      saveSubsection();
      this.saveTimer = null;
    }, 500);
  }
}

function autosaveInput(e) {
  if(this.saveTimer) {
    clearTimeout(this.saveTimer);
  }

  this.saveTimer = setTimeout(function() {        
    $changedInput = $(e.target);
    saveSubsection();
    this.saveTimer = null;
  }, 500);
}

function saveSubsection() {
  if($changedInput && !$changedInput.hasClass('no-spinner')) {
    $spinner.css({
      'position': 'absolute',
      'top': Math.floor($changedInput.position().top + ($changedInput.outerHeight() / 2) + 3),
      'left': $changedInput.position().left + $changedInput.outerWidth() - 24,
      'margin-top': '-10px'
    });
    $changedInput.after($spinner);
    $spinner.show();
  }
  
  var id = $('.subsection-body').data('id');

  // pull all 'normalized' metadata editable fields on page
  var metadata_fields = $('input[data-metadata-name]');
  
  var metadata = {};
  for(var i=0; i< metadata_fields.length;i++) {
     var el = metadata_fields[i];
     metadata[$(el).data("metadata-name")] = el.value;
  } 

  // now add 'free-formed' metadata which are presented to the user as dual input fields (name/value)
  $('ol.policy-list > li.policy-list-element').each( function(i, element) {
    var name = $(element).children('.policy-list-name').val();
    metadata[name] = $(element).children('.policy-list-value').val();
  });

  // now add any 'removed' policy metadata which is stored in a separate hidden div
  // 'null' presented to the server means 'remove'
  $("#policy-to-delete > li.policy-list-element").each(function(i, element) {
    var name = $(element).children('.policy-list-name').val();
    if (name != "")
       metadata[name] = null;
  });

  // Piece back together the date/time UI elements into one date/time string
  // NOTE: our various "date/time" metadata elements don't always utilize the same formatting string
  // so make sure we're passing back the correct format
  metadata['start'] = getEdxTimeFromDateTimeInputs('start_date', 'start_time');
  metadata['due'] = getEdxTimeFromDateTimeInputs('due_date', 'due_time', 'MMMM dd HH:mm');

  $.ajax({
    url: "/save_item",
    type: "POST",
    dataType: "json",
    contentType: "application/json",
    data:JSON.stringify({ 'id' : id, 'metadata' : metadata}),
    success: function() {
      $spinner.delay(500).fadeOut(150);
    },
    error: function() {
      showToastMessage('There has been an error while saving your changes.');
    }
  });
}


function createNewUnit(e) {
  e.preventDefault();

  parent = $(this).data('parent');
  template = $(this).data('template');

  $.post('/clone_item',
     {'parent_location' : parent,
       'template' : template,
       'display_name': 'New Unit'
       },
     function(data) {
       // redirect to the edit page
       window.location = "/edit/" + data['id'];
     });
}

function deleteUnit(e) {
  e.preventDefault();
  _deleteItem($(this).parents('li.leaf'));
}

function deleteSubsection(e) {
  e.preventDefault();
  _deleteItem($(this).parents('li.branch'));
}

function deleteSection(e) {
  e.preventDefault();
  _deleteItem($(this).parents('section.branch'));
}

function _deleteItem($el) {
   if(!confirm('Are you sure you wish to delete this item. It cannot be reversed!'))
     return;
      
  var id = $el.data('id');
  
  $.post('/delete_item', 
     {'id': id, 'delete_children' : true, 'delete_all_versions' : true}, 
     function(data) {
       $el.remove();
     });
}

function showUploadModal(e) {
  e.preventDefault();
  $modal = $('.upload-modal').show();
  $('.file-input').bind('change', startUpload);
  $modalCover.show();
}

function showFileSelectionMenu(e) {
  e.preventDefault();
  $('.file-input').click();
}

function startUpload(e) {
  $('.upload-modal h1').html('Uploading…');
  $('.upload-modal .file-name').html($('.file-input').val().replace('C:\\fakepath\\', ''));
  $('.upload-modal .file-chooser').ajaxSubmit({
    beforeSend: resetUploadBar,
    uploadProgress: showUploadFeedback,
    complete: displayFinishedUpload
  });
  $('.upload-modal .choose-file-button').hide();
  $('.upload-modal .progress-bar').removeClass('loaded').show();
}

function resetUploadBar(){
  var percentVal = '0%';
  $('.upload-modal .progress-fill').width(percentVal);
  $('.upload-modal .progress-fill').html(percentVal);
}

function showUploadFeedback(event, position, total, percentComplete) {
  var percentVal = percentComplete + '%';
  $('.upload-modal .progress-fill').width(percentVal);
  $('.upload-modal .progress-fill').html(percentVal);
}

function displayFinishedUpload(xhr) {
  if(xhr.status = 200){
    markAsLoaded();
  }

  var resp = JSON.parse(xhr.responseText);
  $('.upload-modal .embeddable-xml-input').val(xhr.getResponseHeader('asset_url'));
  $('.upload-modal .embeddable').show();
  $('.upload-modal .file-name').hide();
  $('.upload-modal .progress-fill').html(resp.msg);
  $('.upload-modal .choose-file-button').html('Load Another File').show();
  $('.upload-modal .progress-fill').width('100%');

  // see if this id already exists, if so, then user must have updated an existing piece of content
  $("tr[data-id='" + resp.url + "']").remove();

  var template = $('#new-asset-element').html();
  var html = Mustache.to_html(template, resp);
  $('table > tbody').prepend(html);

}

function markAsLoaded() {
  $('.upload-modal .copy-button').css('display', 'inline-block');
  $('.upload-modal .progress-bar').addClass('loaded');
}    

function hideModal(e) {
  if(e) {
    e.preventDefault();
  }
  // Unit editors do not want the modal cover to hide when users click outside
  // of the editor. Users must press Cancel or Save to exit the editor.
  // module_edit adds and removes the "is-fixed" class.
  if (!$modalCover.hasClass("is-fixed")) {
    $('.file-input').unbind('change', startUpload);
    $modal.hide();
    $modalCover.hide();
  }
}

function onKeyUp(e) {
  if(e.which == 87) {
    $body.toggleClass('show-wip hide-wip');
  }
}

function toggleSubmodules(e) {
  e.preventDefault();
  $(this).toggleClass('expand').toggleClass('collapse');
  $(this).closest('.branch, .window').toggleClass('collapsed');
}

function setVisibility(e) {
  $(this).find('.checked').removeClass('checked');
  $(e.target).closest('.option').addClass('checked');
}

function editComponent(e) {
  e.preventDefault();
  $(this).closest('.xmodule_edit').addClass('editing').find('.component-editor').slideDown(150);
}

function closeComponentEditor(e) {
  e.preventDefault();
  $(this).closest('.xmodule_edit').removeClass('editing').find('.component-editor').slideUp(150);
}

function showDateSetter(e) {
  e.preventDefault();
  var $block = $(this).closest('.due-date-input');
  $(this).hide();
  $block.find('.date-setter').show();
}

function removeDateSetter(e) {
  e.preventDefault();
  var $block = $(this).closest('.due-date-input');
  $block.find('.date-setter').hide();
  $block.find('.set-date').show();
  // clear out the values
  $block.find('.date').val('');
  $block.find('.time').val('');
}

function showToastMessage(message, $button, lifespan) {
  var $toast = $('<div class="toast-notification"></div>');
  var $closeBtn = $('<a href="#" class="close-button">×</a>');
  $toast.append($closeBtn);
  var $content = $('<div class="notification-content"></div>');
  $content.html(message);
  $toast.append($content);
  if($button) {
    $button.addClass('action-button');
    $button.bind('click', hideToastMessage);
    $content.append($button);
  }
  $closeBtn.bind('click', hideToastMessage);

  if($('.toast-notification')[0]) {
    var targetY = $('.toast-notification').offset().top + $('.toast-notification').outerHeight();
    $toast.css('top', (targetY + 10) + 'px');
  }

  $body.prepend($toast);
  $toast.fadeIn(200);

  if(lifespan) {
    $toast.timer = setTimeout(function() {
      $toast.fadeOut(300);
    }, lifespan * 1000);
  }
}

function hideToastMessage(e) {
  e.preventDefault();
  $(this).closest('.toast-notification').remove();
}

function addNewSection(e, isTemplate) {
  e.preventDefault();

  $(e.target).addClass('disabled');

  var $newSection = $($('#new-section-template').html());
  var $cancelButton = $newSection.find('.new-section-name-cancel');
  $('.courseware-overview').prepend($newSection);
  $newSection.find('.new-section-name').focus().select();
  $newSection.find('.section-name-form').bind('submit', saveNewSection);
  $cancelButton.bind('click', cancelNewSection);
  $body.bind('keyup', { $cancelButton: $cancelButton }, checkForCancel);
}

function checkForCancel(e) {
  if(e.which == 27) {
    $body.unbind('keyup', checkForCancel);
    e.data.$cancelButton.click();
  }
}


function saveNewSection(e) {
  e.preventDefault();

  var $saveButton = $(this).find('.new-section-name-save');
  var parent = $saveButton.data('parent');
  var template = $saveButton.data('template');
  var display_name = $(this).find('.new-section-name').val();

  $.post('/clone_item', {
      'parent_location' : parent,
      'template' : template,
      'display_name': display_name,
    },
    function(data) {
      if (data.id != undefined)
        location.reload();
    }
  );
}

function cancelNewSection(e) {
  e.preventDefault();
  $('.new-courseware-section-button').removeClass('disabled');
  $(this).parents('section.new-section').remove();
}

function addNewCourse(e) {
  e.preventDefault();

  $(e.target).hide();
  $('.content .introduction').hide();
  var $newCourse = $($('#new-course-template').html());
  var $cancelButton = $newCourse.find('.new-course-cancel');
  $('.inner-wrapper').prepend($newCourse);
  $newCourse.find('.new-course-name').focus().select();
  $newCourse.find('form').bind('submit', saveNewCourse);
  $cancelButton.bind('click', cancelNewCourse);
  $body.bind('keyup', { $cancelButton: $cancelButton }, checkForCancel);
}

function saveNewCourse(e) {
  e.preventDefault();

  var $newCourse = $(this).closest('.new-course');
  var template = $(this).find('.new-course-save').data('template');
  var org = $newCourse.find('.new-course-org').val();
  var number = $newCourse.find('.new-course-number').val();
  var display_name = $newCourse.find('.new-course-name').val();

  if (org == '' || number == '' || display_name == ''){
    alert('You must specify all fields in order to create a new course.');
    return;
  }

  $.post('/create_new_course', {
    'template' : template,
    'org' : org,
    'number' : number,
    'display_name': display_name
    },
    function(data) {
      if (data.id != undefined) {
        window.location = '/' + data.id.replace(/.*:\/\//, '');
      } else if (data.ErrMsg != undefined) {
        alert(data.ErrMsg);
      }
    });
}

function cancelNewCourse(e) {
  e.preventDefault();
  $('.new-course-button').show();
  $('.content .introduction').show();
  $(this).parents('section.new-course').remove();
}

function addNewSubsection(e) {
  e.preventDefault();
  var $section = $(this).closest('.courseware-section');
  var $newSubsection = $($('#new-subsection-template').html());
  $section.find('.subsection-list > ol').append($newSubsection);
  $section.find('.new-subsection-name-input').focus().select();

  var $saveButton = $newSubsection.find('.new-subsection-name-save');
  var $cancelButton = $newSubsection.find('.new-subsection-name-cancel');

  var parent = $(this).parents("section.branch").data("id");

  $saveButton.data('parent', parent);
  $saveButton.data('template', $(this).data('template'));

  $newSubsection.find('.new-subsection-form').bind('submit', saveNewSubsection);
  $cancelButton.bind('click', cancelNewSubsection);
  $body.bind('keyup', { $cancelButton: $cancelButton }, checkForCancel);
}

function saveNewSubsection(e) {
  e.preventDefault();

  var parent = $(this).find('.new-subsection-name-save').data('parent');
  var template = $(this).find('.new-subsection-name-save').data('template');

  var display_name = $(this).find('.new-subsection-name-input').val();

  $.post('/clone_item', {
    'parent_location' : parent,
    'template' : template,
    'display_name': display_name
    },
    function(data) {
      if (data.id != undefined) {
        location.reload();             
      }
    }
  );
}

function cancelNewSubsection(e) {
  e.preventDefault();
  $(this).parents('li.branch').remove();
}

function editSectionName(e) {
  e.preventDefault();
  $(this).unbind('click', editSectionName);
  $(this).children('.section-name-edit').show();
  $(this).find('.edit-section-name').focus();
  $(this).children('.section-name-span').hide();
  $(this).find('.section-name-edit').bind('submit', saveEditSectionName);
  $(this).find('.edit-section-name-cancel').bind('click', cancelNewSection);
  $body.bind('keyup', { $cancelButton: $(this).find('.edit-section-name-cancel') }, checkForCancel);
}

function cancelEditSectionName(e) {
  e.preventDefault();
  $(this).parent().hide();
  $(this).parent().siblings('.section-name-span').show();
  $(this).closest('.section-name').bind('click', editSectionName);
  e.stopPropagation();
}

function saveEditSectionName(e) {
  e.preventDefault();

  $(this).closest('.section-name').unbind('click', editSectionName);

  var id = $(this).closest('.courseware-section').data('id');
  var display_name = $.trim($(this).find('.edit-section-name').val());

  $(this).closest('.courseware-section .section-name').append($spinner);
  $spinner.show();

  if (display_name == '') {
    alert("You must specify a name before saving.");
    return;
  }

  var $_this = $(this);
    // call into server to commit the new order
  $.ajax({
    url: "/save_item",
    type: "POST",
    dataType: "json",
    contentType: "application/json",
    data:JSON.stringify({ 'id' : id, 'metadata' : {'display_name' : display_name}})
  }).success(function()
  {
    $spinner.delay(250).fadeOut(250);
    $_this.closest('h3').find('.section-name-span').html(display_name).show();
    $_this.hide();
    $_this.closest('.section-name').bind('click', editSectionName);
    e.stopPropagation();
  });
}

function setSectionScheduleDate(e) {
  e.preventDefault();
  $(this).closest("h4").hide();
  $(this).parent().siblings(".datepair").show();
}

function cancelSetSectionScheduleDate(e) {
  e.preventDefault();
  $(this).closest(".datepair").hide();
  $(this).parent().siblings("h4").show();
}

function saveSetSectionScheduleDate(e) {
  e.preventDefault();

  var input_date = $('.edit-subsection-publish-settings .start-date').val();
  var input_time = $('.edit-subsection-publish-settings .start-time').val();

  var start = getEdxTimeFromDateTimeVals(input_date, input_time);

  var id = $modal.attr('data-id');

  // call into server to commit the new order
  $.ajax({
    url: "/save_item",
    type: "POST",
    dataType: "json",
    contentType: "application/json",
    data:JSON.stringify({ 'id' : id, 'metadata' : {'start' : start}})
  }).success(function()
  {
    var $thisSection = $('.courseware-section[data-id="' + id + '"]');
    $thisSection.find('.section-published-date').html('<span class="published-status"><strong>Will Release:</strong> ' + input_date + ' at ' + input_time + '</span><a href="#" class="edit-button" data-date="' + input_date + '" data-time="' + input_time + '" data-id="' + id + '">Edit</a>');
    $thisSection.find('.section-published-date').animate({
      'background-color': 'rgb(182,37,104)'
    }, 300).animate({
      'background-color': '#edf1f5'
    }, 300).animate({
      'background-color': 'rgb(182,37,104)'
    }, 300).animate({
      'background-color': '#edf1f5'
    }, 300);
    
    hideModal();
  });
}
