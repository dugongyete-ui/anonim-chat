const mongoose = require('mongoose')

mongoose.connect(process.env.MONGO_URI)
    .then(() => {
        console.log('✔ Database Connected')
    }).catch((err) => {
        console.error('✘ MONGODB ERROR: ', err.message)
    })
