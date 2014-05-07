// Build StaffDebug object
var StaffDebug = (function(){

  get_current_url = function() {
    return window.location.pathname;
  }

  get_url = function(action){
    var pathname = this.get_current_url();
    var url = pathname.substr(0,pathname.indexOf('/courseware')) + '/' + action;
    return url;
  }

  get_user = function(locname){
    var uname = $('#sd_fu_' + locname).val();
    if (uname==""){
        uname =  $('#sd_fu_' + locname).attr('placeholder');
    }
    return uname;
  }

  do_idash_action = function(locname, idaction){
    var pdata = {
        'action': idaction,
        'problem_for_student': locname,
        'unique_student_identifier': get_user(locname)
    }

    $.ajax({
        type: "POST",
        url: get_url('instructor'),
        data: pdata,
        success: function(data){
            var msg = $("#idash_msg", data);
            $("#result_" + locname).html( msg );
        },
        error: function(request, status, error) {
            var text = _.template(
                gettext('Something has gone wrong with this request.  \
                     The server replied with a status of: {error}'),
                {error: error},
                {interpolate: /\{(.+?)\}/g}
            )
            var html = _.template(
                '<p id="idash_msg"><font color="red">{text}</font></p>',
                {text: text},
                {interpolate: /\{(.+?)\}/g}
            )
            $("#result_"+locname).html(html);
        },
        dataType: 'html'
    });
  }

  reset = function(locname){
    do_idash_action(locname, "Reset student's attempts");
  }

  sdelete = function(locname){
    do_idash_action(locname, "Delete student state for module");
  }

  return {
      reset: reset,
      sdelete: sdelete,
      do_idash_action: do_idash_action,
      get_current_url: get_current_url,
      get_url: get_url,
      get_user: get_user
  }
})();

// Register click handlers
$(document).ready(function() {
    $('#staff-debug-reset').click(function() {
        StaffDebug.reset($(this).data('location'));
        return false;
    });
    $('#staff-debug-sdelete').click(function() {
        StaffDebug.sdelete($(this).data('location'));
        return false;
    });
});
