migrate((app) => {
  const collection = new Collection({
    "name": "transcripts",
    "type": "base",
    "system": false,
    "fields": [
      {
        "name": "video_id",
        "type": "text",
        "required": true,
        "presentable": false,
        "min": null,
        "max": null,
        "pattern": ""
      },
      {
        "name": "url",
        "type": "url",
        "required": true,
        "presentable": false,
        "exceptDomains": null,
        "onlyDomains": null
      },
      {
        "name": "full_transcript",
        "type": "text",
        "required": true,
        "presentable": false,
        "min": null,
        "max": null,
        "pattern": ""
      },
      {
        "name": "simple_transcript",
        "type": "text",
        "required": true,
        "presentable": false,
        "min": null,
        "max": null,
        "pattern": ""
      },
      {
        "name": "language",
        "type": "text",
        "required": true,
        "presentable": false,
        "min": null,
        "max": 10,
        "pattern": ""
      },
      {
        "name": "summary",
        "type": "text",
        "required": false,
        "presentable": false,
        "min": null,
        "max": null,
        "pattern": ""
      },
      {
        "name": "created",
        "type": "autodate",
        "onCreate": true,
        "onUpdate": false
      },
      {
        "name": "updated",
        "type": "autodate",
        "onCreate": true,
        "onUpdate": true
      }
    ],
    "indexes": [
      "CREATE INDEX idx_video_id ON transcripts (video_id)"
    ],
    "listRule": "",
    "viewRule": "",
    "createRule": "",
    "updateRule": "",
    "deleteRule": "",
    "options": {}
  });

  app.save(collection);
}, (app) => {
  const collection = app.findCollectionByNameOrId("transcripts");

  app.delete(collection);
})
