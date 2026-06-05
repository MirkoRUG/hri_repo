
from session import SessionWrapper
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
            - Create a story together.
            - Your turns should be at most 2 short sentences.
            - Always build on the child's idea.
            - Be positive and encouraging.
            - Never take over the whole story.
            - Always finish by asking what happens next.
            - Keep the story fun and age-appropriate.
            """
        }
    ]

    yield s.session.call(
        "rie.dialogue.say_animated",
        text="Let's make up a story together! I will start, then you tell me what happens next."
    )

    response = s.client.chat.completions.create(
        messages=story_history + [
            {
                "role": "user",
                "content": "Start a fun story in one short sentence and ask what happens next."
            }
        ],
        model=s.model,
        temperature=0.7
    )

    robot_turn = response.choices[0].message.content or ""

    story_history.append({
        "role": "assistant",
        "content": robot_turn
    })

    NUM_ROUNDS = 5
    for stage in range(1, NUM_ROUNDS + 1):

        child_response = yield s.say_and_listen(robot_turn)

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

                Continue the story in 1-2 short sentences.
                Build on the child's idea.
                End by asking what happens next."""
                }
            ],
            model=s.model,
            temperature=0.7
        )

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
