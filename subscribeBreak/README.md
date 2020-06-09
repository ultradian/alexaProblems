# subscribeBreak
**Problem**: if you have mp3 playing using an SSML audio tag, and the user interrupts with "subscribe me", instead of going to an internal "subscribe me" Intent, it leaves the skill and triggers the Amazon Music

**Recreate**:
use [`model.json`](model.json) as interaction model and [`lambda_function.py`](lambda_function.py) as endpoint code. I served off of AWS lambda and created mp3 `subscriptiontest.mp3` for the audio tag. Feel free to use whatever mp3 you like. I am serving from https://solutones.s3.amazonaws.com/subscriptiontest.mp3 if you want to use that.

The audio mp3 will immediately start playing. Interrupt Alexa by saying "subscribe me". This *ought* to trigger the SubscriptionIntent.
