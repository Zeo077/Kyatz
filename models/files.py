from datetime import datetime

db.define_table('files',
    Field('file_url', 'string'),
    Field('file_id', 'integer')
    )