"""lambda_function.py: subscribe error demo skill."""
import requests
import json

# --------------- context keys -----------------
# CONTEXT keys, values don't matter but must be consistent in code
START_STATE = 'start state'

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
IS_SUBSCRIBER = 'is a subscriber'
ISP_ID = 'ISP product id'
STATE = 'conversation state'

ISP_ENDPOINT = "/v1/users/~current/skills/~current/inSkillProducts/" # noqa

SHORT_PAUSE = "<break time='1s'/> "

VOCAB = {
    'en-US': {
        'messages': {
            'CAN_BUY': "You can buy a subscription to Tone Therapy premium. "
                       "<break time='0.5s'/> Each time you open Tone Therapy "
                       "Premium you’ll hear a different tone session. "
                       "There’s no repetition. Just say, I want tone therapy "
                       "premium. Until then ",
            'NO_ISP': "Sorry, I can't seem to connect to the Amazon "
                      "purchasing service right now. ",
        }
    },
}


# --------------- entry point -----------------
def lambda_handler(event, context):
    """App entry point."""
    print("DEBUG: in lambda_handler", event)
    request_type = event['request']['type']
    if event['request']['type'] == 'Connections.Response':
        return process_isp_response(event)
    elif (('new' in event['session'] and event['session']['new']) or
          request_type == 'LaunchRequest'):
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
    attributes = get_attributes(event)
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
    return play_response(event)


def process_isp_response(event):
    """Manage Connections.Response response."""
    print(f"DEBUG: got Connections.Response:{event}")
    attributes = get_attributes(event)
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
        elif purchase_result == "ERROR":
            print("WARNING: ERROR for Buy in process_isp_response")
        else:
            print("ERROR: illegal value from purchase transaction",
                  purchase_result)
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
        else:
            print("ERROR: illegal value in Upsell transaction",
                  purchase_result)
    else:
        print("WARNING: unhandled request name in process_isp_response",
              event['request'])
    return play_response(event)


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
        directive['payload']['upsellMessage'] = "Upsell product. "
    return directive


def on_intent(event):
    """Process intent."""
    intent_name = event['request']['intent']['name']
    print("on_intent: " + intent_name)
    if intent_name in ('AMAZON.StopIntent', 'AMAZON.CancelIntent'
                       'AMAZON.NoIntent'):
        return stop_response(event)
    elif intent_name == CAN_BUY_INTENT:
        return process_upsell(event)
    elif intent_name == BUY_INTENT:
        return process_purchase(event)
    elif intent_name == REFUND_INTENT:
        return process_refund(event)
    elif intent_name in ('AMAZON.YesIntent', 'RepeatIntent'):
        return play_response(event)
    elif intent_name == "SubscriptionIntent":
        return subscribe_response(event)
    print("Unhandled intent.")
    return stop_response(event)


def stop_response(event):
    """Give stop message response."""
    return service_response({}, tell_response("OK. Bye."))


def subscribe_response(event):
    """Give subscribe Intent response."""
    reprompt = "Do you want to try again?"
    response = ask_response("You successfully triggered the "
                            "subscription intent. " + reprompt, reprompt)
    return service_response({}, response)


def play_response(event):
    """Play the audio mp3."""
    reprompt = "Do you want to try again?"
    response = ask_response("<audio src=\"https://solutones.s3.amazonaws.com/"
                            "subscriptiontest.mp3\" />", reprompt)
    return service_response({}, response)


def process_upsell(event):
    """Process CAN_BUY_INTENT."""
    return play_response(event)


def process_purchase(event):
    """Process BuyIntent."""
#    userId = get_userId(event)
    attributes = get_attributes(event)
    print(f"DEBUG: in process_purchase with {attributes}")
    # this hands off to Amazon
    response = tell_response("")
    response = add_directive(response,
                             isp_directive(event, 'Buy', attributes[ISP_ID]))
#    put_dbdata(DB_TABLE, userId, attributes)
    return service_response(attributes, response)


def process_refund(event):
    """Process RefundIntent."""
#    userId = get_userId(event)
    attributes = get_attributes(event)
    print(f"DEBUG: in process_refund with {attributes}")
    response = tell_response("")
    response = add_directive(response,
                             isp_directive(event,
                                           'Cancel', attributes[ISP_ID]))
#    put_dbdata(DB_TABLE, userId, attributes)
    return service_response(attributes, response)


def on_session_ended(event):
    """Cleanup session."""
    attributes = get_attributes(event)
#    userId = get_userId(event)
    print("on_session_ended: ", attributes)
#    put_dbdata(DB_TABLE, userId, attributes)
    # can't respond to SessionEndedRequest


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
    if 'session' not in event:
        event['session'] = {}
    if 'attributes' not in event['session']:
        event['session']['attributes'] = {}
    return event['session']['attributes']


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
    returns json for an Alexa service response
    """
    return {
        'version': '1.0',
        'sessionAttributes': attributes,
        'response': response
    }
