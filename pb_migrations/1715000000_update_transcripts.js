migrate((app) => {
  const collection = app.findCollectionByNameOrId("transcripts")

  // 1. Add audio_file field
  collection.fields.add(new Field({
    "name": "audio_file",
    "type": "file",
    "required": false,
    "presentable": false,
    "maxSelect": 1,
    "maxSize": 524288000, // 500MB
    "mimeTypes": ["audio/mpeg", "audio/wav", "audio/x-m4a", "audio/mp4", "audio/aac", "audio/ogg", "video/mp4", "video/mpeg", "video/quicktime", "video/webm"],
    "thumbs": [],
    "protected": false
  }))

  // 2. Make video_id optional
  const videoIdField = collection.fields.getByName("video_id")
  videoIdField.required = false
  collection.fields.add(videoIdField) // Re-add replaces the existing field with same name

  // 3. Make url optional
  const urlField = collection.fields.getByName("url")
  urlField.required = false
  collection.fields.add(urlField)

  app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("transcripts")

  // Revert changes
  collection.fields.removeByName("audio_file")

  const videoIdField = collection.fields.getByName("video_id")
  videoIdField.required = true
  collection.fields.add(videoIdField)

  const urlField = collection.fields.getByName("url")
  urlField.required = true
  collection.fields.add(urlField)

  app.save(collection)
})
