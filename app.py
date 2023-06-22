import os
import random

import openai
from deepgram import Deepgram
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

openai.api_key = OPENAI_API_KEY
deepgram = Deepgram(DEEPGRAM_API_KEY)


def get_settings_prompt(transcript):
    return f"""The job that needs to be done

I have a rep on the on phones who is doing a fantastic job. They have the best numbers on the entire team.

I have a call transcript from them and I need to figure out what they're doing on the call that's different and write a new script for all my other reps to follow based on this call transcript.

Here are the guidelines to follow while creating this new script:
1. Make sure to include specific follow up questions the rep asked. The devil is in the details when it comes to what separates an okay rep from the top performing. And it's often these follow up/deepening questions that make a rep great.

2. make sure to include specific language patterns the rep uses. For example, oftentimes the best reps are fairly loose and casual on the phone and sound very natural. It's important you write the script in a way where if another rep follows it closely they'll sound very similar to the high performing rep

3. I want to you extract the core framework, questions, and paragraphs the rep used but do it in a way where it will apply to all prospects/customers, not just the one they talked to in this call. 

4. When writing the script, make sure you write out the script for the entire call. don't cut it short and leave stuff out from the end.

5. Don't change the wording the sales rep used. Don't sterilize the rep, simply format questions in a way where they'll apply to most prospects

6. ONLY output what the sales rep should say, anytime there should be a prospect response simply insert *WFPTR*

7. It's very important to recognize when the rep is pitching a program or offering the prospect/customer something. When you recognize they are pitching something, you should write out all those paragraphs word for word.

8. Make sure to put "Rep:" before each new line in the script.

9. Remember to include all relevant questions about the prospects goals, pains, problems etc in the script

10. Follow this format for writing the script:
Rep:
lorem ipsum

*WFPTR*

Rep:
Lorem ipsum

Here is the call transcript:
{transcript}

Before you write the script tell me Which speaker is the sales rep (they may be labeled as speaker 0, speaker 1, or speaker 2 or a communication of multiple)

Output your answer in this format:
Speaker:

START SCRIPT:

Rep:

Below is the answer you have written based on this while adhering to all the guidelines I gave you:"""


def get_closing_prompt(transcript):
    return f"""The job that needs to be done

I have a sales rep on the on phones who is doing a fantastic job. They have the best numbers on the entire team.

I have a call transcript from them and I need to figure out what they're doing on the call that's different and write a new script for all my other reps to follow based on this call transcript.

Here are the guidelines to follow while creating this new script:
1. Make sure to include specific follow up questions the rep asked. The devil is in the details when it comes to what separates an okay rep from the top performing. And it's often these follow up/deepening questions that make a rep great.

2. make sure to include specific language patterns the rep uses. For example, oftentimes the best reps are fairly loose and casual on the phone and sound very natural. It's important you write the script in a way where if another rep follows it closely they'll sound very similar to the high performing rep

3. I want to you extract the core framework, questions, and paragraphs the rep used but do it in a way where it will apply to all prospects/customers, not just the one they talked to in this call. 

4. When writing the script, make sure you write out the script for the entire call. don't cut it short and leave stuff out from the end.

5. Don't change the wording the sales rep used. Don't sterilize the rep, simply format questions in a way where they'll apply to most prospects

6. ONLY output what the sales rep should say, anytime there should be a prospect response simply insert *WFPTR*

7. It's very important to recognize when the rep is pitching a program or offering the prospect/customer something. When you recognize they are pitching something, you should write out all those paragraphs word for word.

8. Make sure to put "Rep:" before each new line in the script.

9. Remember to include all relevant questions about the prospects goals, pains, problems etc in the script

10. Follow this format for writing the script:
Rep:
lorem ipsum

*WFPTR*

Rep:
Lorem ipsum

Here is the call transcript:
{transcript}

Before you write the script tell me Which speaker is the sales rep (they may be labeled as speaker 0, speaker 1, or speaker 2 or a communication of multiple)

Output your answer in this format:
Speaker:

START SCRIPT:

Rep:

Below is the answer you have written based on this while adhering to all the guidelines I gave you:"""

def generate_file_name():
    random_file_name = ''.join(
        random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(8))

    return random_file_name


def generate_data(messages):
    if messages is None:
        messages = []
    return openai.ChatCompletion.create(
        model="gpt-4-32k-0613",
        temperature=0,
        top_p=1,
        messages=messages,
        max_tokens=2048,
        stream=True
    )


@app.route('/status', methods=['GET'])
def status_checking():
    return "Server is up now."


@app.route('/api/upload_record', methods=['POST'])
def upload_record():
    if "record" not in request.files:
        return "Record file required"

    record = request.files['record']
    file_name = record.filename
    mimetype = record.mimetype
    extension = file_name.split(".")[-1]

    new_file_name = generate_file_name() + '.' + extension

    folder_path = "upload/record"
    file_path = os.path.join(folder_path, new_file_name)

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    record.save(file_path)

    return jsonify({
        "file_name": new_file_name,
        "mimetype": mimetype
    })


@app.route('/api/get_transcript', methods=['POST'])
def get_transcript():
    data = request.json
    folder_path = "upload/record"
    file_path = os.path.join(folder_path, data['file_name'])
    mimetype = data['mimetype']

    with open(file_path, 'rb') as audio:
        # ...or replace mimetype as appropriate
        source = {'buffer': audio, 'mimetype': mimetype}
        response = deepgram.transcription.sync_prerecorded(
            source,
            {
                'punctuate': True,
                'tier': 'nova',
                'model': 'phonecall'
            }
        )

        transcript = response['results']['channels'][0]['alternatives'][0]['transcript']

    os.remove(file_path)

    return transcript


@app.route('/api/get_script_v2', methods=['POST'])
def get_script_v2():
    transcript = request.json['transcript']
    messages = []
    coming_messages = request.json['messages']
    type = request.json['type']

    if type == 'settings' or type == 'customer_service':
        prompt = get_settings_prompt(transcript)
    else:
        prompt = get_closing_prompt(transcript)

    initial_message = {
        "role": "user",
        "content": prompt
    }

    messages.append(initial_message)
    if len(coming_messages) > 0:
        messages.extend(coming_messages)

    def event_stream():
        for line in generate_data(messages=messages):
            text = line.choices[0].delta.get('content', '')
            if len(text):
                yield text

    return Response(event_stream(), mimetype='text/event-stream')


@app.route('/api/get_script', methods=['POST'])
def get_script():
    transcript = request.json['transcript']
    prompt = f"""
        OBJECTIVE
        I have a super high performing rep on the phones. I want to figure out what they are doing differently and create a templatized script that all my other reps can follow.
        
        Your job is based on a transcript of a call, to create a script that all the other reps can follow to perform as good as the top person.
        
        You've been trained on billions of hours of sales, customer service and other calls and are amazing doing this.
        
        TRANSCRIPT:
        "
        {transcript}
        "
        
        Here are the guidelines to follow when thinking about how to reverse engineer the script:
        - exclude what the prospect said - only include what the sales rep should say because obviously the prospect responses weren't in the rep's original scirpt
        - make sure to include ALL deepening/probing/follow questions the rep asked from the transcript as those are absolutely vital to the call and great to have in the script
        - DO NOT SKIP ANY DEEPENING QUESTIONS. include the clarifying questions the rep asked like what do you mean by that, why XYZ, tell me more about that, asking questions about problems, goals etc
        - don't include any personal information about the prospect/customer in the script like name, location, goal etc. instead use brackets like [prospect name] or [income goal] or [insert problem they just said]
        - anywhere the prospect shared their goals/pains, replace that with [insert what they just said here]. Remember, it needs to be formatted to apply to most prospects or customers
        - don't make the script too specific to the prospect. remember, you are reverse engineering the original script the rep was following and it is not hyper customized to any specific person. but do include follow up questions from the script
        - REMEMBER - don't include any personal information in the script about the prospect/customer in the script like name, location, goal etc. instead use brackets like [prospect name] or [income goal] or [insert problem they just said]
        - DONT do any special formatting like bullets, etc.
        - REMEMBER!!!! THIS SCRIPT MUST APPLY TO ANY AND ALL PROSPECTS
        
        WRITE A SCRIPT BASED ON THE TRANSCRIPT THAT OTHER REPS CAN FOLLOW TO GET SIMILAR PERFORMANCE AND RESULTS:
    """
    messages = []
    initial_message = {
        "role": "user",
        "content": prompt
    }
    messages.append(initial_message)
    return generate_data(messages)


@app.route('/api/get_reformatted_script', methods=['POST'])
def get_reformatted_script():
    prompt = "Write summary of following conversation:\n"
    transcript = request.json['transcript']
    prompt = prompt + transcript
    return generate_data(prompt)


if __name__ == '__main__':
    app.run()
