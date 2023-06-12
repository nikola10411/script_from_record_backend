import os
import random

import openai
from deepgram import Deepgram
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

openai.api_key = OPENAI_API_KEY
deepgram = Deepgram(DEEPGRAM_API_KEY)


def generate_file_name():
    random_file_name = ''.join(
        random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(8))

    return random_file_name


def generate_data(prompt):
    script_response = openai.Completion.create(
        prompt=prompt,
        model="text-davinci-003",
        temperature=0.9,
        top_p=1,
        frequency_penalty=0.5,
        presence_penalty=1,
        max_tokens=1024
    )

    return script_response.choices[0].text.strip()


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
            }
        )

        transcript = response['results']['channels'][0]['alternatives'][0]['transcript']

    return transcript


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

    return generate_data(prompt)


@app.route('/api/get_reformatted_script', methods=['POST'])
def get_reformatted_script():
    prompt = "Write summary of following conversation:\n"
    transcript = request.json['transcript']
    prompt = prompt + transcript
    return generate_data(prompt)


if __name__ == '__main__':
    app.run()
