
from session import SessionWrapper
import logging
from twisted.internet.defer import inlineCallbacks

@inlineCallbacks
def run(s: SessionWrapper):
    """Collaborative storytelling game.

    The robot and child take turns adding to a story.
    """

    story_stage_instructions = {
        1: "Keep the story simple and concrete.",
        2: "Introduce a small challenge or mystery.",
        3: "Add emotions and character motivations.",
        4: "Add imaginative or unexpected elements.",
        5: "Build toward an exciting ending."
    }

    story_history = [
        {
            "role": "developer",
            "content": f""" You are playing a collaborative storytelling game with a child with Developmental Language Disorder (DLD).

            Rules:
            - Create a story together. IT IS NOT A REAL STORY, so just continue the fictional story. Create fictional ideas as you go.
            - Use the information in {s.human_context} and {s.conversation_context} to choose the topic of the story.
            - Your turns should be at most 2 short sentences.
            - The story should remain in third person, and you should bring new ideas that continue the child's response. 
            - Be positive and encouraging.
            - In case of speech impediments from the child, be understanding and encouraging.  
            - Never take over the whole story.
            - Always finish by asking what happens next.
            - Keep the story fun and age-appropriate.
            - Always give an idea to continue the story and then ask the child what happens next. 
            """
        }
    ]

    yield s.say("Let's create a story together! I will start, then you tell me what happens next.")

    response = s.client.chat.completions.create(
        messages=story_history + [
            {
                "role": "developer",
                "content": "Start a fun story in one short sentence and ask what happens next."
            }
        ],
        model=s.model,
        temperature=0.7
    )

    robot_speech = response.choices[0].message.content or ""

    story_history.append({
        "role": "assistant",
        "content": robot_speech
    })

    NUM_ROUNDS = 5
    for stage in range(1, NUM_ROUNDS + 1):

        child_response = yield s.say_and_listen(robot_speech)

        story_history.append({
            "role": "user",
            "content": child_response
        })

        response = s.client.chat.completions.create(
            messages=story_history + [
                {
                    "role": "developer",
                    "content": f"""Current story stage: {stage}

                Stage instruction: {story_stage_instructions[stage]}
                
                Do not repeat the first phrase. 
                Continue the story in 1-2 short sentences. Bring new ideas to the conversation so that it does ot get boring, but still follows the topic and the response. 
                Build on the child's idea. Create a story together. IT IS NOT A REAL STORY, so just continue the fictional story. Create fictional ideas as you go.
                End by asking what happens next.
                """
                }
            ],
            model=s.model,
            temperature=0.7
        )
        
        robot_speech = s.get_llm_response(child_response)
        logging.info(f"Robot speech: {robot_speech}")

    yield s.session.call(
        "rie.dialogue.say_animated",
        text="That was a great story! Thank you for playing this game with me! Let's hear a short summary."
    )

    summary_response = s.client.chat.completions.create(
        messages=story_history + [
            {
                "role": "user",
                "content": "Summarize the completed story in exactly 3 short sentences."
            }
        ],
        model=s.model,
        temperature=0.3
    )

    summary = summary_response.choices[0].message.content or ""

    yield s.session.call(
        "rie.dialogue.say_animated",
        text=summary
    )
