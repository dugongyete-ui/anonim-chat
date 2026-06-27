const Queue = require('./models/Queue')
const Room = require('./models/Room')

const { Telegram } = require('telegraf')
const tg = new Telegram(process.env.BOT_TOKEN)

const { Markup } = require('telegraf')

const text = require(`./config/lang/${process.env.LANGUAGE || 'EN'}`)

class MatchMaker {

    async #tryMatch() {
        const queues = await Queue.find({}).limit(2)
        if (queues.length >= 2) {
            const newParticipan = []
            for (const q of queues) {
                await Queue.deleteOne({ user_id: q.user_id })
                newParticipan.push(q.user_id)
            }
            await this.createRoom(newParticipan)
        }
    }

    async createRoom(newParticipan) {
        try {
            let room = new Room({ participans: newParticipan })
            const data = await room.save()
            newParticipan.forEach(id => {
                tg.sendMessage(id, text.CREATE_ROOM.SUCCESS_1)
            })
            console.log(data)
        } catch (err) {
            console.error(err)
        }
    }

    async find(userID) {
        try {
            const inQueue = await Queue.find({ user_id: userID })
            if (inQueue.length > 0) {
                tg.sendMessage(userID, text.FIND.WARNING_1)
                return
            }

            const inRoom = await Room.find({ participans: userID })
            if (inRoom.length > 0) {
                tg.sendMessage(userID, text.FIND.WARNING_2)
                return
            }

            tg.sendMessage(userID, text.FIND.LOADING)
            let queue = new Queue({ user_id: userID })
            await queue.save()

            await this.#tryMatch()
        } catch (err) {
            console.log(err)
        }
    }

    async next(userID) {
        try {
            const doc = await Room.findOneAndDelete({ participans: userID })
            if (doc) {
                let participans = doc.participans
                participans.forEach(id => {
                    if (userID === id) {
                        tg.sendMessage(userID, text.NEXT.SUCCESS_1)
                        this.find(userID)
                    } else {
                        tg.sendMessage(id, text.NEXT.SUCCESS_2)
                    }
                })
            } else {
                tg.sendMessage(userID, text.NEXT.WARNING_1)
            }
        } catch (err) {
            console.log(err)
        }
    }

    async stop(userID) {
        try {
            const doc = await Room.findOneAndDelete({ participans: userID })
            if (doc) {
                let participans = doc.participans
                participans.forEach(id => {
                    if (userID === id) {
                        tg.sendMessage(userID, text.STOP.SUCCESS_1)
                    } else {
                        tg.sendMessage(id, text.STOP.SUCCESS_2)
                    }
                })
            } else {
                tg.sendMessage(userID, text.STOP.WARNING_1)
            }
        } catch (err) {
            console.log(err)
        }
    }

    async exit(userID) {
        try {
            const doc = await Queue.findOneAndDelete({ user_id: userID })
            if (doc != null) {
                tg.sendMessage(userID, text.EXIT.SUCCESS_1)
            } else {
                tg.sendMessage(userID, text.EXIT.WARNING_1)
            }
        } catch (err) {
            console.log(err)
        }
    }

    async connect(userID, [type, data]) {
        try {
            const res = await Room.find({ participans: userID })
            if (res.length > 0) {
                let participans = res[0].participans
                let index = participans.indexOf(userID)
                let partnerID = participans[index == 1 ? 0 : 1]

                switch (type) {
                    case 'text':
                        if (data.reply_to_message) {
                            this.#sendReply(partnerID, userID, data.text, data, 'sendMessage')
                                .catch(err => this.#errorWhenRoomActive(err, userID))
                        } else {
                            tg.sendMessage(partnerID, data.text)
                                .catch(err => this.#errorWhenRoomActive(err, userID))
                        }
                        break
                    case 'sticker':
                        if (data.reply_to_message) {
                            this.#sendReply(partnerID, userID, data.sticker.file_id, data, 'sendSticker')
                                .catch(err => this.#errorWhenRoomActive(err, userID))
                        } else {
                            tg.sendSticker(partnerID, data.sticker.file_id)
                                .catch(err => this.#errorWhenRoomActive(err, userID))
                        }
                        break
                    case 'voice':
                        if (data.reply_to_message) {
                            this.#sendReply(partnerID, userID, data.voice.file_id, data, 'sendVoice')
                                .catch(err => this.#errorWhenRoomActive(err, userID))
                        } else {
                            tg.sendVoice(partnerID, data.voice.file_id)
                                .catch(err => this.#errorWhenRoomActive(err, userID))
                        }
                        break
                    case 'photo':
                        tg.getFileLink(data)
                            .then(url => {
                                let photoName = url.pathname.split('/photos/')[1]
                                tg.sendMessage(partnerID, text.USER_SEND_PHOTO.WARNING_1,
                                    Markup.inlineKeyboard([
                                        [Markup.button.callback('Buka', 'openPhoto-' + String(photoName))],
                                    ])
                                ).catch(err => this.#errorWhenRoomActive(err, userID))
                            }).catch(err => console.log(err))
                        break
                    case 'video':
                        tg.getFileLink(data)
                            .then(url => {
                                let videoName = url.pathname.split('/videos/')[1]
                                tg.sendMessage(partnerID, text.USER_SEND_VIDEO.WARNING_1,
                                    Markup.inlineKeyboard([
                                        [Markup.button.callback('Buka', 'openVideo-' + String(videoName))],
                                    ])
                                ).catch(err => this.#errorWhenRoomActive(err, userID))
                            }).catch(err => console.log(err))
                        break
                    default:
                        break
                }
            } else {
                tg.sendMessage(userID, text.CONNECT.WARNING_1)
                    .catch(err => console.log(err))
            }
        } catch (err) {
            console.log(err)
        }
    }

    async currentActiveUser(userID) {
        let totalUserInRoom = await Room.countDocuments() * 2
        let totalUserInQueue = await Queue.countDocuments()
        let totalUser = totalUserInRoom + totalUserInQueue
        let textActiveUser = text.ACTIVE_USER
            .replace('${totalUser}', totalUser)
            .replace('${totalUserInQueue}', totalUserInQueue)
            .replace('${totalUserInRoom}', totalUserInRoom)

        tg.sendMessage(userID, textActiveUser)
    }

    async #forceStop(userID) {
        try {
            const doc = await Room.findOneAndDelete({ participans: userID })
            if (doc) {
                let participans = doc.participans
                participans.forEach(id => {
                    if (userID === id) {
                        tg.sendMessage(userID, text.STOP.SUCCESS_2)
                    }
                })
            }
        } catch (err) {
            console.log(err)
        }
    }

    #errorWhenRoomActive({ response, on }, userID) {
        console.log(response, on)
        switch (response.error_code) {
            case 403:
                this.#forceStop(userID)
                break
            default:
                break
        }
    }

    #sendReply(partnerID, userID, dataToSend, dataReply, type) {
        let { photo, video, message_id, from: { id } } = dataReply.reply_to_message

        let number = photo || video ? 2 : 1
        let replyToPlus = { reply_to_message_id: message_id + number }
        let replyToMinus = { reply_to_message_id: message_id - number }

        id == userID ?
            tg[type](partnerID, dataToSend, replyToPlus) :
            tg[type](partnerID, dataToSend, replyToMinus)
    }
}

module.exports = MatchMaker
