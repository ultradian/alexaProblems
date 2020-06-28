"""lambda_function.py: lambda test ffmpeg skill."""
import random
from datetime import datetime
from decimal import Decimal
import requests
import json
import boto3
from botocore.exceptions import ClientError

__version__ = '0.2.0'
__author__ = 'Milton Huang'

PRINT_LIMIT = 33    # to shorten debug output

# --------------- context keys -----------------
# CONTEXT keys, values don't matter but must be consistent in code
START_STATE = 'start state'
TONE_FOLLOWUP_STATE = 'answer TONE_FOLLOWUP state'

# --------------- intent names -----------------
# must match the names in model.json
BUY_INTENT = 'BuyIntent'
CAN_BUY_INTENT = 'CanBuyIntent'
REFUND_INTENT = 'RefundIntent'

# --------------- slots names -----------------
# must match the name of the slot in model.json
DURATION_SLOT = 'duration'

# --------------- attributes keys -----------------
# labels for Attribute keys, values don't matter but can't change unless
#   you update names in the database.  Should all be unique.
SPEECHOUTPUT = 'speechOutput'
REPROMPT = 'repromptText'
VISIT_COUNT = 'number of visits'
FREE_COUNT = 'number of free plays'
SUBSCRIBER_COUNT = 'number of subscriber plays'
IS_SUBSCRIBER = 'is a subscriber'
ISP_ID = 'ISP product id'
MIX_INDEX = 'index of mix tone'
MIX_HASH = 'uuid for filename'
CURRENT_PLAYTIME = 'cummulative mix duration'
TARGET_DURATION = 'target mix duration'
STATE = 'conversation state'

# --------------- DynamoDB names -----------------
USERID = 'userId'   # table key
DATA = 'data'       # table record
TIMESTAMP = 'timestamp'       # table record

# local version
# DYNAMODB = boto3.resource('dynamodb', region_name='us-east-1',
#                           endpoint_url='http://localhost:8000')
DYNAMODB = boto3.resource('dynamodb', region_name='us-east-1')
DB_TABLE_NAME = 'ToneTherapyTable'
DB_TABLE = DYNAMODB.Table(DB_TABLE_NAME)

TONE_BUCKET = boto3.resource('s3').Bucket('solutonetherapytones')
TONE_CLIENT = boto3.client('s3')
URL_PREFIX = "https://solutonetherapytones.s3.amazonaws.com/"
FREE_LIST = [x.key[5:] for x in TONE_BUCKET.objects.filter(Prefix='free')
             if x.key != 'free/']
SOURCE_LIST = [x.key[7:] for x in TONE_BUCKET.objects.filter(Prefix='source')
               if x.key != 'source/']
print(f"Free list:{FREE_LIST}\nSource list:{SOURCE_LIST}")

ISP_ENDPOINT = "/v1/users/~current/skills/~current/inSkillProducts/" # noqa

SHORT_PAUSE = "<break time='1s'/> "

VOCAB = {
    'en-US': {
        'messages': {
            'WELCOME_MESSAGE': "Welcome to Tone Therapy. When you return to "
                               "this skill in the future, I’ll play a three "
                               "minute session of peaceful, healing tones. "
                               "These are free samples that have been "
                               "pre-recorded. If you would like to hear "
                               "tone sessions created for you in the moment "
                               "just say, what can I buy? ",
            'STOP_MESSAGE': "Ok. Goodbye! ",
            'FREE_HELP': "One of three, free, pre-recorded, Tone Therapy "
                         "sessions will play for three minutes each time you "
                         "say Alexa, open tone therapy. The premium version "
                         "of Tone Therapy offers Tone Therapy sessions that "
                         "are composed in the moment just for you, and "
                         "they never repeat. And, you won’t hear my voice "
                         "every time. You can learn more by saying, tell "
                         "me about premium. Now, ",
            'SUBSCRIBER_HELP': "When I ask, Just say, play for, the number "
                               "of minutes or hours you want to play. ",
            'CONFUSED_TIME': "I’m confused about how long you want the "
                             "tones to play. Please try again. ",
            'CONFUSED_YES': "I’m sorry, but I don't understand what you are "
                            "saying yes for. ",
            'CONFUSED_NO': "I’m sorry, but I don't understand what you are "
                           "saying no for. ",
            'FREE_FALLBACK': "I'm sorry, I don't understand what you want. "
                             "You can say, Alexa, help, for more help. Here "
                             "is another free tone. ",
            'FALLBACK_MESSAGE': "I'm sorry, I don't understand what you want. "
                                "Try again. ",
            'FALLBACK_REPROMPT': "Please try asking that a different way. ",
            'BAD_PROBLEM': "I'm sorry, something happened that shouldn't "
                           "have. Please Try again. ",
            'BAD_GENERATOR': "Sorry, there is something wrong with my mixing "
                             "system. Please try again later. Goodbye.",
            'FREE_INTRO_1': "<audio src=\"" + URL_PREFIX +
                            "messages/this_is_ruane_for_solu.mp3\" /> ",
            'FREE_INTRO_2': "<audio src=\"" + URL_PREFIX +
                            "messages/Created_on_Marthas_Vineyard.mp3\" /> ",
            'FREE_INTRO_3': "<audio src=\"" + URL_PREFIX +
                            "messages/If_you_want_to_learn_more.mp3\" /> ",
            'FREE_INTRO_4': "<audio src=\"" + URL_PREFIX +
                            "messages/Tone_Therapy_3_minutes.mp3\" /> ",
            'FREE_INTRO_5': "This is free play intro message number 5. ",
            'FREE_INTRO_6': "This is free play intro message number 6. ",
            'MIX_INTRO_1': "Welcome to Tone Therapy Premium. Take a deep "
                           "breath, relax, and,<break time='1s'/> just "
                           "listen. ",
            'MIX_INTRO_2': "Welcome back. Remember you can ask for help. "
                           "Just say, Alexa, help. As the tones play, don’t "
                           "worry if your mind wanders, just bring your "
                           "focus back to the tones. Now take a deep breath. "
                           "Relax. <break time='1s'/> Here you go. ",
            'MIX_INTRO_3': "Great job. You’re learning to be a focused "
                           "listener! Oh, if after 7 days you decide Tone "
                           "Therapy Premium is not for you, just say, "
                           "cancel my subscription. And this is the last "
                           "time you’ll hear my voice before your Tone "
                           "Therapy premium sessions. Remember, you can "
                           "say, exit, help, or, cancel my subscription, if "
                           "you interrupt the tone by saying, Alexa. "
                           "<break time='1s'/> Now here’s your Tone Therapy "
                           "session. ",
            'CAN_BUY': "You can buy a subscription to Tone Therapy premium. "
                       "<break time='0.5s'/> Each time you open Tone Therapy "
                       "Premium you’ll hear a different tone session. "
                       "There’s no repetition. Just say, I want tone therapy "
                       "premium. Until then ",
            'UPSELL_MESSAGE': "Tone Therapy premium offers Tone Therapy "
                              "sessions that never repeat, they’re composed "
                              "in the moment, just for you. And you won’t "
                              "hear my voice before each tone therapy "
                              "session. Do you want to learn more? ",
            'ALREADY_SUBSCRIBE': "Congratulations, you already have a "
                                 "subscription. ",
            'FREE_TONE': "<audio src=\"" + URL_PREFIX +
                         "messages/OK_here_is_session.mp3\" /> ",
            'FREE_FOLLOWUP': "<break time='5s'/><audio src=\"" + URL_PREFIX +
                             "messages/AnotherSession1.mp3\" /> ",
            'TONE_FOLLOWUP': "<break time='5s'/><prosody volume='-3dB'>"
                             "<amazon:effect name='whispered'>Again?"
                             "</amazon:effect></prosody> ",
            'NO_ISP': "Sorry, I can't seem to connect to the Amazon "
                      "purchasing service right now. ",
        }
    },
}


# --------------- entry point -----------------
def lambda_handler(event, context):
    """App entry point."""
    print(f"DEBUG: in lambda_handler with {event}")
    request_type = event['request']['type']
    if event['request']['type'] == 'Connections.Response':
        return process_isp_response(event)
    elif (('session' in event and 'new' in event['session'] and
           event['session']['new']) or request_type == 'LaunchRequest'):
            return on_launch(event)
    elif request_type == 'IntentRequest':
        return on_intent(event)
    elif event['request']['type'] == 'SessionEndedRequest':
        return on_session_ended(event)
    else:
        print("WARNING: Unhandled event in lambda_handler:", event)
        return stop_response(event)


# --------------- request handlers -----------------
def on_launch(event):
    """Start session."""
    userId = get_userId(event)
    attributes = get_dbdata(DB_TABLE, userId)
    print(f"DEBUG: in on_launch with {event}")
    messages = get_message(get_locale(event))
    speechmessage = ""
    if attributes is None or VISIT_COUNT not in attributes:
        # first time
        attributes[VISIT_COUNT] = 0
        attributes[FREE_COUNT] = 0
        attributes[SUBSCRIBER_COUNT] = 0
        attributes[IS_SUBSCRIBER] = False
        speechmessage = messages['WELCOME_MESSAGE'] + SHORT_PAUSE
    attributes[VISIT_COUNT] += 1
    attributes[STATE] = START_STATE
    isp_response = get_isp(event)
    if isp_response == {}:
        # can't buy or sell
        attributes[ISP_ID] = ""
    else:
        # assuming single product
        attributes[ISP_ID] = isp_response['inSkillProducts'][0]['productId']
        if isp_response['inSkillProducts'][0]['entitled'] == 'ENTITLED':
            attributes[IS_SUBSCRIBER] = True
        else:
            attributes[IS_SUBSCRIBER] = False
    print(f"DEBUG: updated_subscription {attributes}")
    put_dbdata(DB_TABLE, userId, attributes)
    if not attributes[IS_SUBSCRIBER]:
        return play_free_tone(event, speechmessage)
    return play_mix_tone(event)


def process_isp_response(event):
    """Manage Connections.Response response."""
    print(f"DEBUG: got Connections.Response:{event}")
    userId = get_userId(event)
    attributes = get_attributes(event)
    messages = get_message(get_locale(event))
    if 'purchaseResult' not in event['request']['payload']:
        print("ERROR: no purchaseResult in isp_response")
        speechmessage = SHORT_PAUSE
    purchase_result = event['request']['payload']['purchaseResult']
    if event['request']['name'] == 'Buy':
        if purchase_result == "ACCEPTED":
            attributes[IS_SUBSCRIBER] = True
            speechmessage = SHORT_PAUSE
            # need messages['SUBSCRIBE_SUCCESS'] if Amazon doesn't say it
        elif purchase_result == "DECLINED":
            attributes[IS_SUBSCRIBER] = False
            # need messages['DECLINED_RESPONSE'] if Amazon doesn't say it
            speechmessage = SHORT_PAUSE
        elif purchase_result == "ALREADY_PURCHASED":
            if not attributes[IS_SUBSCRIBER]:
                print("ERROR: ALREADY_PURCHASED when not IS_SUBSCRIBER",
                      attributes)
                attributes[IS_SUBSCRIBER] = True
            speechmessage = messages['ALREADY_SUBSCRIBE']
        elif purchase_result == "ERROR":
            speechmessage = messages['NO_ISP'] + SHORT_PAUSE
            print("WARNING: ERROR for Buy in process_isp_response")
        else:
            print("ERROR: illegal value from purchase transaction",
                  purchase_result)
            return confused_response(event)
    elif event['request']['name'] == 'Cancel':
        if purchase_result == "ACCEPTED":
            speechmessage = SHORT_PAUSE
            attributes[IS_SUBSCRIBER] = False
        elif purchase_result == "DECLINED":
            speechmessage = SHORT_PAUSE
        elif purchase_result == "ALREADY_PURCHASED":
            # can this even happen?
            print("got ALREADY_PURCHASED from ISP Cancel request")
            speechmessage = SHORT_PAUSE
        elif purchase_result == "ERROR":
            print("WARNING: ERROR for Cancel in process_isp_response")
            speechmessage = messages['NO_ISP'] + SHORT_PAUSE
        else:
            speechmessage = SHORT_PAUSE
            print("ERROR: illegal value in Cancel transaction",
                  purchase_result)
    elif event['request']['name'] == 'Upsell':
        if purchase_result == "ACCEPTED":
            speechmessage = SHORT_PAUSE
        elif purchase_result == "DECLINED":
            speechmessage = SHORT_PAUSE
        elif purchase_result == "ALREADY_PURCHASED":
            speechmessage = SHORT_PAUSE
        elif purchase_result == "ERROR":
            print("WARNING: ERROR for Upsell in process_isp_response")
            speechmessage = messages['NO_ISP'] + SHORT_PAUSE
        else:
            speechmessage = SHORT_PAUSE
            print("ERROR: illegal value in Upsell transaction",
                  purchase_result)
    else:
        print("WARNING: unhandled request name in process_isp_response",
              event['request'])
        return confused_response(event)
    put_dbdata(DB_TABLE, userId, attributes)
    return choice_ending(event, speechmessage)


def on_intent(event):
    """Process intent."""
    intent_name = event['request']['intent']['name']
    print(f"on_intent: {intent_name}")
    if intent_name in ('AMAZON.StopIntent', 'AMAZON.CancelIntent'):
        return stop_response(event)
    elif intent_name == 'AMAZON.HelpIntent':
        return help_response(event)
    elif intent_name == CAN_BUY_INTENT:
        return process_upsell(event)
    elif intent_name == BUY_INTENT:
        return process_purchase(event)
    elif intent_name == REFUND_INTENT:
        return process_refund(event)
    elif intent_name == 'AMAZON.YesIntent':
        return process_yes(event)
    elif intent_name == 'AMAZON.NoIntent':
        return process_no(event)
    else:
        print("WARNING: unhandled intent in on_intent", intent_name)
        return confused_response(event)


def stop_response(event):
    """Give stop message response."""
    userId = get_userId(event)
    attributes = get_attributes(event)
    messages = get_message(get_locale(event))
    put_dbdata(DB_TABLE, userId, attributes)
    response = tell_response(messages['STOP_MESSAGE'])
    return service_response(attributes, response)


def help_response(event):
    """Give help response."""
    messages = get_message(get_locale(event))
    attributes = get_attributes(event)
    if attributes[IS_SUBSCRIBER]:
        speechmessage = messages['SUBSCRIBER_HELP']
    else:
        speechmessage = messages['FREE_HELP']
    return choice_ending(event, speechmessage)


def confused_response(event):
    """Return FALLBACK_MESSAGE response."""
    messages = get_message(get_locale(event))
    attributes = get_attributes(event)
    if attributes[IS_SUBSCRIBER]:
        speechmessage = messages['FALLBACK_MESSAGE']
        reprompt = messages['FALLBACK_REPROMPT']
        response = ask_response(speechmessage, reprompt)
        return service_response(attributes, response)
    speechmessage = messages['FREE_FALLBACK']
    return play_free_tone(event, speechmessage)


def choice_ending(event, speechmessage=""):
    """Send either free_play or mix_play based on IS_SUBSCRIBER."""
    attributes = get_attributes(event)
    if attributes[IS_SUBSCRIBER]:
        return play_mix_tone(event, speechmessage)
    else:
        return play_free_tone(event, speechmessage)


def process_yes(event):
    """Process YesIntent."""
    attributes = get_attributes(event)
    messages = get_message(get_locale(event))
    print(f"entering process_yes with {attributes}")
    if attributes[STATE] == TONE_FOLLOWUP_STATE:
        attributes[STATE] = START_STATE
        if not attributes[IS_SUBSCRIBER]:
            return play_free_tone(event)
        return play_mix_tone(event)
    else:
        print("WARNING: unhandled _state in process_yes", attributes[STATE])
        speechmessage = messages['CONFUSED_YES']
    if not attributes[IS_SUBSCRIBER]:
        return play_free_tone(event, speechmessage)
    return play_mix_tone(event, speechmessage)


def process_no(event):
    """Process NoIntent."""
    attributes = get_attributes(event)
    messages = get_message(get_locale(event))
    if attributes[STATE] == TONE_FOLLOWUP_STATE:
        attributes[STATE] = START_STATE
        return stop_response(event)
    else:
        print(f"WARNING: unhandled _state in process_no {attributes[STATE]}")
        speechmessage = messages['CONFUSED_NO']
    if not attributes[IS_SUBSCRIBER]:
        return play_free_tone(event, speechmessage)
    return play_mix_tone(event, speechmessage)


def process_upsell(event):
    """Process CAN_BUY_INTENT."""
    attributes = get_attributes(event)
    messages = get_message(get_locale(event))
    if attributes[IS_SUBSCRIBER]:
        speechmessage = messages['ALREADY_SUBSCRIBE']
        return play_mix_tone(event, speechmessage)
    speechmessage = messages['CAN_BUY']
    return play_free_tone(event, speechmessage)


def process_purchase(event):
    """Process BuyIntent."""
    userId = get_userId(event)
    attributes = get_attributes(event)
    print(f"DEBUG: in process_purchase with {attributes}")
    messages = get_message(get_locale(event))
    # this hands off to Amazon
    if attributes[IS_SUBSCRIBER]:
        speechmessage = messages['ALREADY_SUBSCRIBE']
        return play_mix_tone(event, speechmessage)
    if attributes[ISP_ID] == "":
        speechmessage = messages['NO_ISP']
        return play_free_tone(event, speechmessage)
    response = tell_response("")
    response = add_directive(response,
                             isp_directive(event, 'Buy', attributes[ISP_ID]))
    put_dbdata(DB_TABLE, userId, attributes)
    return service_response(attributes, response)


def process_refund(event):
    """Process RefundIntent."""
    userId = get_userId(event)
    attributes = get_attributes(event)
    print(f"DEBUG: in process_refund with {attributes}")
    response = tell_response("")
    response = add_directive(response,
                             isp_directive(event,
                                           'Cancel', attributes[ISP_ID]))
    put_dbdata(DB_TABLE, userId, attributes)
    return service_response(attributes, response)


def on_session_ended(event):
    """Cleanup session."""
    attributes = get_attributes(event)
    userId = get_userId(event)
    print("on_session_ended: ", attributes)
    put_dbdata(DB_TABLE, userId, attributes)
    # can't respond to SessionEndedRequest


# ------------------------------ request helpers -----------------
def play_free_tone(event, speechmessage=""):
    """Play tone from free folder on S3."""
    userId = get_userId(event)
    attributes = get_attributes(event)
    messages = get_message(get_locale(event))
    attributes[FREE_COUNT] += 1
    speechmessage += messages['FREE_TONE']
    output = ("<audio src=\"https://solutones.s3.amazonaws.com/"
              "subscriptiontest.mp3\" />")
    # if attributes[FREE_COUNT] % 2 == 0:
    #     response = tell_response(output + "<break time='5s'/>")
    #     response = add_directive(response,
    #                              isp_directive(event,
    #                                            'Upsell', attributes[ISP_ID]))
    #     put_dbdata(DB_TABLE, userId, attributes)
    #     return service_response(attributes, response)
    attributes[STATE] = TONE_FOLLOWUP_STATE
    output += messages['FREE_FOLLOWUP']
    reprompt = messages['FREE_FOLLOWUP']
    put_dbdata(DB_TABLE, userId, attributes)
    response = ask_response(output, reprompt)
    return service_response(attributes, response)


def play_mix_tone(event, speechmessage=""):
    """Play tone mix using source folder on S3."""
    attributes = get_attributes(event)
    reprompt = "Do you want to try again?"
    response = ask_response("<audio src=\"https://solutones.s3.amazonaws.com/"
                            "subscriptiontest.mp3\" />", reprompt)
    return service_response(attributes, response)


def get_isp(event):
    """Get in-skill products list."""
    api_endpoint = event['context']['System']['apiEndpoint']
    locale = get_locale(event)
    token = get_access_token(event)
    url = f"{api_endpoint}{ISP_ENDPOINT}"
    print(f"checking isp at {url}")
    headers = {'Authorization': f'Bearer {token}',
               'Accept-Language': f'{locale}',
               'Accept': 'application/json'}
    try:
        r = requests.get(url=url, headers=headers)
    except requests.exceptions.Timeout:
        # consider retry vs message
        print("Timeout error in get_isp")
        return {}
    except requests.exceptions.ConnectionError as e:
        print("Connection error in get_isp:", e)
        # connection error message
        return {}
    if r.status_code == requests.codes.ok:
        isp = json.loads(r.text)
        print("in get_isp, got response:", isp)
        return isp
    else:
        print("bad request in get_isp that did not raise exception:",
              r.text)
        return {}


def isp_directive(event, request_type, product_id):
    """Return SendRequest directive for ISP.

    request_type should be 'Buy', 'Cancel', or 'Upsell'
    see https://developer.amazon.com/docs/in-skill-purchase/add-isps-to-a-skill.html#cancel-requests # noqa
    """
    print(f"DEBUG: sending isp_directive {request_type} for {product_id}")
    directive = {
        "type": "Connections.SendRequest",
        "name": request_type,
        "payload": {
            "InSkillProduct": {
              "productId": product_id
            }
        },
        "token": "subscriptionToken"
    }
    if request_type == 'Upsell':
        messages = get_message(get_locale(event))
        directive['payload']['upsellMessage'] = messages['UPSELL_MESSAGE']
    return directive


# ------------------------------ request helpers -----------------
def get_message(locale):
    """Get message strings for `locale`."""
    return VOCAB[locale]['messages']


def get_locale(event):
    """Get locale from event."""
    request = event['request']
    if 'locale' in request:
        locale = request['locale']
    else:
        locale = 'en-US'
    return locale


def get_userId(event):
    """Get userId from event."""
    userId = event['context']['System']['user']['userId']
    print("userId: ", userId)
    return userId


def get_access_token(event):
    """Get api access token from request."""
    if 'apiAccessToken' in event['context']['System']:
        token = event['context']['System']['apiAccessToken']
        print("get_access_token: ", token)
        if token:
            return token
    print("ERROR: no token in get_access_token:", event)
    return ""


def get_attributes(event, attr=''):
    """Return session['attributes'] object."""
    if 'session' not in event or 'attributes' not in event['session']:
        userId = get_userId(event)
        attributes = get_dbdata(DB_TABLE, userId)
        if attributes is not None:
            return attributes
        return {}
    return event['session']['attributes']


# --------------- data helpers -----------------
def clear_empty_strings(data):
    """Replace empty strings in data with ' '."""
    for key in data:
        if data[key] == '':
            data[key] = ' '
        if isinstance(data[key], float):
            data[key] = int(data[key])
        elif isinstance(data, dict):
            if data[key] == '':
                data[key] = ' '
            if isinstance(data[key], float):
                data[key] = int(data[key])
            if isinstance(data[key], (dict, list)):
                data[key] = clear_empty_strings(data[key])
    return data


def restore_empty_strings(data):
    """Replace ' ' with empty strings in data."""
    for i, key in enumerate(data):
        if isinstance(data, list):
            if key == " ":
                data[i] = ""
            if isinstance(key, Decimal):
                data[i] = int(data[i])
            if isinstance(key, (dict, list)):
                data[i] = restore_empty_strings(data[i])
        elif isinstance(data, dict):
            if data[key] == ' ':
                data[key] = ''
            if isinstance(data[key], Decimal):
                data[key] = int(data[key])
            if isinstance(data[key], (dict, list)):
                data[key] = restore_empty_strings(data[key])
    return data


def get_dbdata(table, id):
    """
    Fetch data for user.

    Args:
    table -- dynamodb table
    id -- userId to fetch
    """
    # TODO: if Requested resource not found, handle it
    try:
        response = table.get_item(
            Key={
                USERID: id
            }
        )
        print("get response:", response)
    except ClientError as e:
        error_msg = e.response['Error']['Message']
        print("WARNING: error in get_dbdata:", error_msg)
        if error_msg == "Requested resource not found":
            # no table
            print("WARNING: creatng new table in get_dbdata")
            table = make_dynamodb_table(DB_TABLE_NAME)
        item = {}
    else:
        if 'Item' not in response:
            print("Creating since No Item in get_dbdata:", response)
            put_dbdata(table, id, {})
            return {}
        if DATA in response['Item']:
            item = response['Item'][DATA]
            item = restore_empty_strings(item)
            print("GetItem succeeded: ", item)
        else:
            item = {}
    return item


def put_dbdata(table, id, data):
    """
    Save data for user.

    Args:
    table -- dynamodb table
    id -- userId to save to

    Returns:
    response

    """
    data = clear_empty_strings(data)
    try:
        response = table.put_item(
            Item={
                USERID: id,
                DATA: data,
                TIMESTAMP: datetime.utcnow().isoformat()
            }
        )
    except ClientError as e:
        error_msg = e.response['Error']['Message']
        print("WARNING: error in put_dbdata:", error_msg)
        # if error_msg == "Requested resource not found":
        # no table TODO: make this work
        return e.response['Error']['Message']
    else:
        print("PutItem succeeded: " + id[0:PRINT_LIMIT])
        return response


def make_dynamodb_table(name):
    """Return a new DynamoDB table."""
    return DYNAMODB.create_table(
        TableName=name,
        KeySchema=[
            {
                'AttributeName': 'userId',
                'KeyType': 'HASH'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'userId',
                'AttributeType': 'S'
            },

        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )


# --------------- speech response handlers -----------------
# build the json responses
# https://developer.amazon.com/public/solutions/alexa/alexa-skills-kit/docs/alexa-skills-kit-interface-reference
# response text cannot exceed 8000 characters
# response size cannot exceed 24 kilobytes

def tell_response(output):
    """Create a simple json tell response."""
    return {
        'outputSpeech': {
            'type': 'SSML',
            'ssml': "<speak>" + output + "</speak>"
        },
        'shouldEndSession': True
    }


def ask_response(output, reprompt):
    """Create a json ask response."""
    return {
        'outputSpeech': {
            'type': 'SSML',
            'ssml': "<speak>" + output + "</speak>"
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'SSML',
                'ssml': "<speak>" + reprompt + "</speak>"
            }
        },
        'shouldEndSession': False
    }


def add_directive(response, directive):
    """Append directive to response field in response."""
    if not directive:
        return response
    if 'directives' not in response:
        response['directives'] = []
    response['directives'].append(directive)
    print("DEBUG: add_directive", directive)
    return response


def service_response(attributes, response):
    """Create a simple json response.

    uses one of the speech_responses (`tell_response`, `ask_response`)
    can also create response from `add_directive`
    returns json for an Alexa service response
    """
    return {
        'version': '1.0',
        'sessionAttributes': attributes,
        'response': response
    }
