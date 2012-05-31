describe 'VideoSpeedControl', ->
  beforeEach ->
    @player = jasmine.stubVideoPlayer @
    $('.speeds').remove()

  afterEach ->

  describe 'constructor', ->
    describe 'always', ->
      beforeEach ->
        @speedControl = new VideoSpeedControl @player, @video.speeds

      it 'add the video speed control to player', ->
        expect($('.secondary-controls').html()).toContain '''
          <div class="speeds">
            <a href="#">
              <h3>Speed</h3>
              <p class="active">1.0x</p>
            </a>
            <ol class="video_speeds"><li data-speed="1.0" class="active"><a href="#">1.0x</a></li><li data-speed="0.75"><a href="#">0.75x</a></li></ol>
          </div>
        '''

      it 'bind to player speedChange event', ->
        expect($(@player)).toHandleWith 'speedChange', @speedControl.onSpeedChange

      it 'bind to change video speed link', ->
        expect($('.video_speeds a')).toHandleWith 'click', @speedControl.changeVideoSpeed

    describe 'when running on touch based device', ->
      beforeEach ->
        spyOn(window, 'onTouchBasedDevice').andReturn true
        $('.speeds').removeClass 'open'
        @speedControl = new VideoSpeedControl @player, @video.speeds

      it 'open the speed toggle on click', ->
        $('.speeds').click()
        expect($('.speeds')).toHaveClass 'open'
        $('.speeds').click()
        expect($('.speeds')).not.toHaveClass 'open'

    describe 'when running on non-touch based device', ->
      beforeEach ->
        spyOn(window, 'onTouchBasedDevice').andReturn false
        $('.speeds').removeClass 'open'
        @speedControl = new VideoSpeedControl @player, @video.speeds

      it 'open the speed toggle on hover', ->
        $('.speeds').mouseenter()
        expect($('.speeds')).toHaveClass 'open'
        $('.speeds').mouseleave()
        expect($('.speeds')).not.toHaveClass 'open'

      it 'close the speed toggle on mouse out', ->
        $('.speeds').mouseenter().mouseleave()
        expect($('.speeds')).not.toHaveClass 'open'

      it 'close the speed toggle on click', ->
        $('.speeds').mouseenter().click()
        expect($('.speeds')).not.toHaveClass 'open'

  describe 'changeVideoSpeed', ->
    beforeEach ->
      @speedControl = new VideoSpeedControl @player, @video.speeds
      @video.setSpeed '1.0'

    describe 'when new speed is the same', ->
      beforeEach ->
        spyOnEvent @player, 'speedChange'
        $('li[data-speed="1.0"] a').click()

      it 'does not trigger speedChange event', ->
        expect('speedChange').not.toHaveBeenTriggeredOn @player

    describe 'when new speed is not the same', ->
      beforeEach ->
        @newSpeed = null
        $(@player).bind 'speedChange', (event, newSpeed) => @newSpeed = newSpeed
        spyOnEvent @player, 'speedChange'
        $('li[data-speed="0.75"] a').click()

      it 'trigger player speedChange event', ->
        expect('speedChange').toHaveBeenTriggeredOn @player
        expect(@newSpeed).toEqual 0.75

  describe 'onSpeedChange', ->
    beforeEach ->
      @speedControl = new VideoSpeedControl @player, @video.speeds
      $('li[data-speed="1.0"] a').addClass 'active'
      @speedControl.setSpeed '0.75'

    it 'set the new speed as active', ->
      expect($('.video_speeds li[data-speed="1.0"]')).not.toHaveClass 'active'
      expect($('.video_speeds li[data-speed="0.75"]')).toHaveClass 'active'
      expect($('.speeds p.active')).toHaveHtml '0.75x'
