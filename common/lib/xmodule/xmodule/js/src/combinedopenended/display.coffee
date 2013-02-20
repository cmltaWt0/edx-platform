class @Rubric
  constructor: () ->

  # finds the scores for each rubric category
  @get_score_list: () =>
    # find the number of categories:
    num_categories = $('.rubric-category').length

    score_lst = []
    # get the score for each one
    for i in [0..(num_categories-1)]
      score = $("input[name='score-selection-#{i}']:checked").val()
      score_lst.push(score)

    return score_lst

  @get_total_score: () ->
    score_lst = @get_score_list()
    tot = 0
    for score in score_lst
      tot += parseInt(score)
    return tot

  @check_complete: () ->
     # check to see whether or not any categories have not been scored
    num_categories = $('.rubric-category').length
    for i in [0..(num_categories-1)]
      score = $("input[name='score-selection-#{i}']:checked").val()
      if score == undefined
        return false
    return true

class @CombinedOpenEnded
  constructor: (element) ->
    @element=element
    @reinitialize(element)

  reinitialize: (element) ->
    @wrapper=$(element).find('section.xmodule_CombinedOpenEndedModule')
    @el = $(element).find('section.combined-open-ended')
    @combined_open_ended=$(element).find('section.combined-open-ended')
    @id = @el.data('id')
    @ajax_url = @el.data('ajax-url')
    @state = @el.data('state')
    @task_count = @el.data('task-count')
    @task_number = @el.data('task-number')
    @accept_file_upload = @el.data('accept-file-upload')

    @allow_reset = @el.data('allow_reset')
    @reset_button = @$('.reset-button')
    @reset_button.click @reset
    @next_problem_button = @$('.next-step-button')
    @next_problem_button.click @next_problem
    @status_container = @$('.status-elements')

    @show_results_button=@$('.show-results-button')
    @show_results_button.click @show_results

    @question_header = @$('.question-header')
    @question_header.click @collapse_question

    # valid states: 'initial', 'assessing', 'post_assessment', 'done'
    Collapsible.setCollapsibles(@el)
    @submit_evaluation_button = $('.submit-evaluation-button')
    @submit_evaluation_button.click @message_post

    @results_container = $('.result-container')
    @combined_rubric_container = $('.combined-rubric-container')

    @legend_container= $('.legend-container')
    @show_legend_current()

    # Where to put the rubric once we load it
    @el = $(element).find('section.open-ended-child')
    @errors_area = @$('.error')
    @answer_area = @$('textarea.answer')
    @prompt_container = @$('.prompt')
    @rubric_wrapper = @$('.rubric-wrapper')
    @hint_wrapper = @$('.hint-wrapper')
    @message_wrapper = @$('.message-wrapper')
    @submit_button = @$('.submit-button')
    @child_state = @el.data('state')
    @child_type = @el.data('child-type')
    if @child_type=="openended"
      @skip_button = @$('.skip-button')
      @skip_button.click @skip_post_assessment

    @file_upload_area = @$('.file-upload')
    @can_upload_files = false
    @open_ended_child= @$('.open-ended-child')

    @out_of_sync_message = 'The problem state got out of sync.  Try reloading the page.'

    if @task_number>1
      @prompt_hide()
    else if @task_number==1 and @child_state!='initial'
      @prompt_hide()

    @find_assessment_elements()
    @find_hint_elements()

    @rebind()

    if @task_number>1
      @show_combined_rubric_current()
      @show_results_current()

  # locally scoped jquery.
  $: (selector) ->
    $(selector, @el)

  show_results_current: () =>
    data = {'task_number' : @task_number-1}
    $.postWithPrefix "#{@ajax_url}/get_results", data, (response) =>
      if response.success
        @results_container.after(response.html).remove()
        @results_container = $('div.result-container')
        @submit_evaluation_button = $('.submit-evaluation-button')
        @submit_evaluation_button.click @message_post
        Collapsible.setCollapsibles(@results_container)

  show_results: (event) =>
    status_item = $(event.target).parent()
    status_number = status_item.data('status-number')
    data = {'task_number' : status_number}
    $.postWithPrefix "#{@ajax_url}/get_results", data, (response) =>
      if response.success
        @results_container.after(response.html).remove()
        @results_container = $('div.result-container')
        @submit_evaluation_button = $('.submit-evaluation-button')
        @submit_evaluation_button.click @message_post
        Collapsible.setCollapsibles(@results_container)
      else
        @gentle_alert response.error

  show_combined_rubric_current: () =>
    data = {}
    $.postWithPrefix "#{@ajax_url}/get_combined_rubric", data, (response) =>
      if response.success
        @combined_rubric_container.after(response.html).remove()
        @combined_rubric_container= $('div.combined_rubric_container')

  show_status_current: () =>
    data = {}
    $.postWithPrefix "#{@ajax_url}/get_status", data, (response) =>
      if response.success
        @status_container.after(response.html).remove()
        @status_container= $('.status-elements')

  show_legend_current: () =>
    data = {}
    $.postWithPrefix "#{@ajax_url}/get_legend", data, (response) =>
      if response.success
        @legend_container.after(response.html).remove()
        @legend_container= $('.legend-container')

  message_post: (event)=>
    Logger.log 'message_post', @answers
    external_grader_message=$(event.target).parent().parent().parent()
    evaluation_scoring = $(event.target).parent()

    fd = new FormData()
    feedback = evaluation_scoring.find('textarea.feedback-on-feedback')[0].value
    submission_id = external_grader_message.find('input.submission_id')[0].value
    grader_id = external_grader_message.find('input.grader_id')[0].value
    score = evaluation_scoring.find("input:radio[name='evaluation-score']:checked").val()

    fd.append('feedback', feedback)
    fd.append('submission_id', submission_id)
    fd.append('grader_id', grader_id)
    if(!score)
      @gentle_alert "You need to pick a rating before you can submit."
      return
    else
      fd.append('score', score)

    settings =
      type: "POST"
      data: fd
      processData: false
      contentType: false
      success: (response) =>
        @gentle_alert response.msg
        $('section.evaluation').slideToggle()
        @message_wrapper.html(response.message_html)

    $.ajaxWithPrefix("#{@ajax_url}/save_post_assessment", settings)


  rebind: () =>
    # rebind to the appropriate function for the current state
    @submit_button.unbind('click')
    @submit_button.show()
    @reset_button.hide()
    @next_problem_button.hide()
    @hide_file_upload()
    @hint_area.attr('disabled', false)
    if @task_number>1 or @child_state!='initial'
      @show_status_current()

    if @task_number==1 and @child_state=='assessing'
      @prompt_hide()
    if @child_state == 'done'
      @rubric_wrapper.hide()
    if @child_type=="openended"
      @skip_button.hide()
    if @allow_reset=="True"
      @show_results_current
      @reset_button.show()
      @submit_button.hide()
      @answer_area.attr("disabled", true)
      @replace_text_inputs()
      @hint_area.attr('disabled', true)
    else if @child_state == 'initial'
      @answer_area.attr("disabled", false)
      @submit_button.prop('value', 'Submit')
      @submit_button.click @save_answer
      @setup_file_upload()
    else if @child_state == 'assessing'
      @answer_area.attr("disabled", true)
      @replace_text_inputs()
      @hide_file_upload()
      @submit_button.prop('value', 'Submit assessment')
      @submit_button.click @save_assessment
      if @child_type == "openended"
        @submit_button.hide()
        @queueing()
    else if @child_state == 'post_assessment'
      if @child_type=="openended"
        @skip_button.show()
        @skip_post_assessment()
      @answer_area.attr("disabled", true)
      @replace_text_inputs()
      @submit_button.prop('value', 'Submit post-assessment')
      if @child_type=="selfassessment"
         @submit_button.click @save_hint
      else
        @submit_button.click @message_post
    else if @child_state == 'done'
      @rubric_wrapper.hide()
      @answer_area.attr("disabled", true)
      @replace_text_inputs()
      @hint_area.attr('disabled', true)
      @submit_button.hide()
      if @child_type=="openended"
        @skip_button.hide()
      if @task_number<@task_count
        @next_problem()
      else
        @show_results_current()
        @reset_button.show()


  find_assessment_elements: ->
    @assessment = @$('input[name="grade-selection"]')

  find_hint_elements: ->
    @hint_area = @$('textarea.post_assessment')

  save_answer: (event) =>
    event.preventDefault()
    max_filesize = 2*1000*1000 #2MB
    if @child_state == 'initial'
      files = ""
      if @can_upload_files == true
        files = $('.file-upload-box')[0].files[0]
        if files != undefined
          if files.size > max_filesize
            @can_upload_files = false
            files = ""
        else
          @can_upload_files = false

      fd = new FormData()
      fd.append('student_answer', @answer_area.val())
      fd.append('student_file', files)
      fd.append('can_upload_files', @can_upload_files)

      settings =
        type: "POST"
        data: fd
        processData: false
        contentType: false
        success: (response) =>
          if response.success
            @rubric_wrapper.html(response.rubric_html)
            @rubric_wrapper.show()
            @answer_area.html(response.student_response)
            @child_state = 'assessing'
            @find_assessment_elements()
            @rebind()
          else
            @gentle_alert response.error

      $.ajaxWithPrefix("#{@ajax_url}/save_answer",settings)

    else
      @errors_area.html(@out_of_sync_message)

  save_assessment: (event) =>
    event.preventDefault()
    if @child_state == 'assessing' && Rubric.check_complete()
      checked_assessment = Rubric.get_total_score()
      score_list = Rubric.get_score_list()
      data = {'assessment' : checked_assessment, 'score_list' : score_list}
      $.postWithPrefix "#{@ajax_url}/save_assessment", data, (response) =>
        if response.success
          @child_state = response.state

          if @child_state == 'post_assessment'
            @hint_wrapper.html(response.hint_html)
            @find_hint_elements()
          else if @child_state == 'done'
            @rubric_wrapper.hide()

          @rebind()
        else
          @errors_area.html(response.error)
    else
      @errors_area.html(@out_of_sync_message)

  save_hint:  (event) =>
    event.preventDefault()
    if @child_state == 'post_assessment'
      data = {'hint' : @hint_area.val()}

      $.postWithPrefix "#{@ajax_url}/save_post_assessment", data, (response) =>
        if response.success
          @message_wrapper.html(response.message_html)
          @child_state = 'done'
          @rebind()
        else
          @errors_area.html(response.error)
    else
      @errors_area.html(@out_of_sync_message)

  skip_post_assessment: =>
    if @child_state == 'post_assessment'

      $.postWithPrefix "#{@ajax_url}/skip_post_assessment", {}, (response) =>
        if response.success
          @child_state = 'done'
          @rebind()
        else
          @errors_area.html(response.error)
    else
      @errors_area.html(@out_of_sync_message)

  reset: (event) =>
    event.preventDefault()
    if @child_state == 'done' or @allow_reset=="True"
      $.postWithPrefix "#{@ajax_url}/reset", {}, (response) =>
        if response.success
          @answer_area.val('')
          @rubric_wrapper.html('')
          @hint_wrapper.html('')
          @message_wrapper.html('')
          @child_state = 'initial'
          @combined_open_ended.after(response.html).remove()
          @allow_reset="False"
          @reinitialize(@element)
          @rebind()
          @reset_button.hide()
        else
          @errors_area.html(response.error)
    else
      @errors_area.html(@out_of_sync_message)

  next_problem: =>
    if @child_state == 'done'
      $.postWithPrefix "#{@ajax_url}/next_problem", {}, (response) =>
        if response.success
          @answer_area.val('')
          @rubric_wrapper.html('')
          @hint_wrapper.html('')
          @message_wrapper.html('')
          @child_state = 'initial'
          @combined_open_ended.after(response.html).remove()
          @reinitialize(@element)
          @rebind()
          @next_problem_button.hide()
          if !response.allow_reset
            @gentle_alert "Moved to next step."
          else
            @gentle_alert "Your score did not meet the criteria to move to the next step."
            @show_results_current()
        else
          @errors_area.html(response.error)
    else
      @errors_area.html(@out_of_sync_message)

  gentle_alert: (msg) =>
    if @el.find('.open-ended-alert').length
      @el.find('.open-ended-alert').remove()
    alert_elem = "<div class='open-ended-alert'>" + msg + "</div>"
    @el.find('.open-ended-action').after(alert_elem)
    @el.find('.open-ended-alert').css(opacity: 0).animate(opacity: 1, 700)

  queueing: =>
    if @child_state=="assessing" and @child_type=="openended"
      if window.queuePollerID # Only one poller 'thread' per Problem
        window.clearTimeout(window.queuePollerID)
      window.queuePollerID = window.setTimeout(@poll, 10000)

  poll: =>
    $.postWithPrefix "#{@ajax_url}/check_for_score", (response) =>
      if response.state == "done" or response.state=="post_assessment"
        delete window.queuePollerID
        location.reload()
      else
        window.queuePollerID = window.setTimeout(@poll, 10000)

  setup_file_upload: =>
    if @accept_file_upload == "True"
      if window.File and window.FileReader and window.FileList and window.Blob
        @can_upload_files = true
        @file_upload_area.html('<input type="file" class="file-upload-box">')
        @file_upload_area.show()
      else
        @gentle_alert 'File uploads are required for this question, but are not supported in this browser. Try the newest version of google chrome.  Alternatively, if you have uploaded the image to the web, you can paste a link to it into the answer box.'

  hide_file_upload: =>
    if @accept_file_upload == "True"
      @file_upload_area.hide()

  replace_text_inputs: =>
    answer_class = @answer_area.attr('class')
    answer_id = @answer_area.attr('id')
    answer_val = @answer_area.val()
    new_text = ''
    new_text = "<div class='#{answer_class}' id='#{answer_id}'>#{answer_val}</div>"
    @answer_area.replaceWith(new_text)

  # wrap this so that it can be mocked
  reload: ->
    location.reload()

  collapse_question: () =>
    @prompt_container.slideToggle()
    @prompt_container.toggleClass('open')
    if @question_header.text() == "(Hide)"
      new_text = "(Show)"
    else
      new_text = "(Hide)"
    @question_header.text(new_text)

  prompt_show: () =>
    if @prompt_container.is(":hidden")==true
      @prompt_container.slideToggle()
      @prompt_container.toggleClass('open')
      @question_header.text("(Hide)")

  prompt_hide: () =>
    if @prompt_container.is(":visible")==true
      @prompt_container.slideToggle()
      @prompt_container.toggleClass('open')
      @question_header.text("(Show)")


