db.createRole({ role: 'feh', privileges: [{ resource: { db: 'feh', collection: 'feh' }, actions: ['find', 'insert', 'update'] }, { resource: { db: 'feh', collection: '' }, actions: ['listCollections', 'listIndexes'] }], roles: [] });
db.createUser({ user: 'feh', pwd: 'feh', roles: [{ role: 'feh', db: 'feh' }] });
