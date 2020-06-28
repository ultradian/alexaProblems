"""lambda_function.py: lambda test scrolling skill."""
import json

APL_TEMPLATE_FN = "apl_selection_template.json"
with open(APL_TEMPLATE_FN) as f:
    APL_TEMPLATE = json.load(f)


# --------------- entry point -----------------
def lambda_handler(event, context):
    """App entry point."""
    print(f"DEBUG: in lambda_handler with {event}")
    request_type = event['request']['type']
    if (('session' in event and 'new' in event['session'] and
         event['session']['new']) or request_type == 'LaunchRequest'):
        return on_launch(event)
    elif request_type == 'IntentRequest':
        return on_intent(event)
    elif event['request']['type'] == 'SessionEndedRequest':
        return on_session_ended(event)
    elif request_type == 'Alexa.Presentation.APL.UserEvent':
        return on_UserEvent(event)
    else:
        print("WARNING: Unhandled event in lambda_handler:", event)
        return stop_response(event)


def on_launch(event):
    """Start session."""
    # check APL device
    print(f"on_launch with {event['context']}")
    supported = event['context']['System']['device']['supportedInterfaces']
    if "Alexa.Presentation.APL" not in supported.keys():
        response = tell_response("you need an APL device for this test. ")
        return service_response({}, response)
    msg = "say scroll right or left. "
    response = ask_response(msg, msg)
    directive = {
        "type": "Alexa.Presentation.APL.RenderDocument",
        "token": "scrollPageToken",
        "document": APL_TEMPLATE['document'],
        "datasources": APL_TEMPLATE['datasources']
    }
    add_directive(response, directive)
    return service_response({}, response)


def on_session_ended(event):
    """Cleanup session."""
    # can't respond to SessionEndedRequest
    return {
        "version": "1.0",
        "response": {}
    }


def on_UserEvent(event):
    """Process on_UserEvent event.

    Could be video_end or touch wrapper
    """
    print("DEBUG: got UserEvent", event)
    arguments = event['request']['arguments']
    if arguments[0] == 'itemSelected':
        print("DEBUG: got itemSelected in on_UserEvent", event['request'])
    else:
        print("WARNING: unrecognized on_UserEvent", event['request'])
        return {}


def on_intent(event):
    """Process intent."""
    intent_name = event['request']['intent']['name']
    print(f"on_intent: {intent_name}")
    if intent_name in ('AMAZON.StopIntent', 'AMAZON.CancelIntent'):
        return stop_response(event)
    elif intent_name in ('AMAZON.ScrollLeftIntent',
                         'AMAZON.ScrollRightIntent'):
        return scroll_response(event)
    else:
        msg = ""
    reprompt = "scroll more or stop. "
    msg += reprompt
    return service_response({}, ask_response(msg, reprompt))


def scroll_response(event):
    """
    Scroll scroll_sequence left or right.

    implemented as described at https://developer.amazon.com/en-US/docs/alexa/alexa-presentation-language/apl-standard-commands.html#scroll-command # noqa
    """
    request = event['request']
    print(f"in scroll_response")
    if request['intent']['name'] == 'AMAZON.ScrollRightIntent':
        distance = 2
        msg = "scrolled right. "
    else:
        distance = -2
        msg = "scrolled left. "
    reprompt = "scroll more or stop. "
    msg += reprompt
    response = ask_response(msg, reprompt)
    # response = add_directive(response, {
    #     "type": "Alexa.Presentation.APL.ExecuteCommands",
    #     "token": "scrollCommandToken",
    #     "commands": [{
    #         "type": "Scroll",
    #         "componentId": "scrollSequence",
    #         "distance": distance
    #     }]
    # })
    return service_response({}, response)


def stop_response(event):
    """Give stop message response."""
    response = tell_response("Goodbye!")
    return service_response({}, response)


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
