class CMS.Models.Module extends Backbone.Model
  url: '/save_item'
  defaults:
    data: ''

  loadModule: (element) ->
    elt = $(element).find('.xmodule_edit').first()
    @module = XModule.loadModule(elt)

  editUrl: ->
    "/edit_item?#{$.param(id: @get('id'))}"

  save: (args...) ->
    @set(data: JSON.stringify(@module.save())) if @module
    super(args...)
