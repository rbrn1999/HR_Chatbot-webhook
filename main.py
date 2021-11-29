import dialogflowClient as dialogflow
import richMenu_handler
import requests, json
from linebot import WebhookHandler, LineBotApi
from linebot.exceptions import InvalidSignatureError
from linebot.models import FollowEvent, TextSendMessage, MessageEvent, TextMessage, PostbackEvent, TemplateSendMessage, URITemplateAction, CarouselTemplate, CarouselColumn
from config import channelSecret, channelAccessToken, WebUrl

# （0） Messages
welcomeMessage = TextSendMessage(text='歡迎加入本公司！!')
registerHandleMessage = TextSendMessage(text='正在為你註冊打卡系統')
registerSuccessText = '已完成註冊打卡系統\n'

# （1） Line webhook
handler = WebhookHandler(channelSecret)
lineBotApi = LineBotApi(channelAccessToken)


def linewebhook(request):
    body = request.get_data(as_text=True)
    signature = request.headers.get("X-Line-Signature")
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("signature error")
    return '200 OK'


# （2） Follow event
@handler.add(FollowEvent)
def handle_follow(event):
    lineId = event.source.user_id
    replyToken = event.reply_token
    richMenu_handler.create_richMenu(lineId=lineId, linebotapi=lineBotApi)
    lineBotApi.reply_message(replyToken, welcomeMessage)
    dialogflowEvent = 'followEvent'
    queryResult = dialogflow.detectIntent(lineId, False, dialogflowEvent)
    handle_queryResult(queryResult, lineId)


# （3） Message event
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    lineId = event.source.user_id
    text = event.message.text
    queryResult = dialogflow.detectIntent(lineId, text, False)
    handle_queryResult(queryResult, lineId)


def handle_queryResult(queryResult, lineId):
    if 'action' in queryResult and queryResult['action'] == "registerAction":
        if queryResult['parameters']['person']['name']:
            lineBotApi.push_message(lineId, registerHandleMessage)
            memberName = queryResult['parameters']['person']['name']
            member = postMemberFlow(lineId, memberName)
            if member:
                message = TextSendMessage(
                    text=registerSuccessText + 'memberId=' + member['id'] + '\n' \
                                             + 'name=' + member['name'] + '\n' \
                                             + 'lineId=' + member['lineId']
                )
                lineBotApi.push_message(lineId, message)
            richMenu_handler.create_richMenu(lineId,linebotapi= lineBotApi, memberId=member["id"], timeflag=False)

    if queryResult['fulfillmentMessages']:
        for n in range(len(queryResult['fulfillmentMessages'])):
            message = TextSendMessage(text=queryResult['fulfillmentMessages'][n]['text']['text'][0])
            lineBotApi.push_message(lineId, message)

# (4) Postback Event
@handler.add(PostbackEvent)
def handle_postback(event):
    if 'clock' in event.postback.data:
        url = event.postback.data
        # url = f"{WebUrl}/clock/" # temporary fake url
        templateMessage = TemplateSendMessage(
            alt_text='請選擇功能 ',
            template=CarouselTemplate(
                columns=[
                    CarouselColumn(
                        thumbnail_image_url='https://www.datamaticsinc.com/wp-content/uploads/2016/09/buddy-punching.jpg',
                        title='打卡系統',
                        text='請點選下列功能',
                        actions=[
                            URITemplateAction(
                                label='上班',
                                uri= WebUrl + '/start_work'
                            ),
                            URITemplateAction(
                                label='下班',
                                uri= WebUrl + '/end_work'
                            ),
                        ]
                    )
                ]
            )
        )
        replyMessages = [templateMessage]
        lineBotApi.reply_message(event.reply_token, replyMessages)
    else:
        lineBotApi.reply_message(event.reply_token, {type: 'text', text: 'template 載入失敗'})
def postMemberFlow(lineId, name):
    # firestore 註冊
    response = requests.post(WebUrl + '/register', json={'name' : name, 'lineId' : lineId})
    member = response.content
    memberToDict = json.loads(member)
    return memberToDict
