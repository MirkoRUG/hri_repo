from session import SessionWrapper
import settings
import logging
from PIL import Image
from twisted.internet.defer import inlineCallbacks
from threading import Thread


# map language level to the image file + metadata
key = {
 0: ('cattle_abduction.jpg', "The image contains a green ufo seen abducting a cow. There are 3 small sprigs visible as well.", 3),
 1: ('zoo.jpg', "The image contains a banner reading 'zoo'; in front of the banner are an elephant, giraffe, panda, and hippo.", 4),
 2: ('construction_site.jpg', "The image depicts a construction site. Visible are 3 pylons, an excavator, and a road roller. A skyline including a crane and skyscrapers is visible in the background. ", 4),
 3: ('ecosystem.jpg', "The iage depicts a wetland ecosystem. In the pictre are a dragonfly, a beaver, a brown bear, a moose, a frog, a duck, a fox, 2 birds, a fish, and an amphibian. There are some reeds, lily pads, and birch and pine trees in the background. ", 11)
} 


@inlineCallbacks
def single_round(s: SessionWrapper, image: str, subjects: str, num_subjects: int):
    """Plays a single round of the image description game.

    :param s: session object
    :param image: image file
    :param subjects: list of subjects the child could identify from the image"""
    num_described: int = 0
    num_turns: int = 0
    human_answer: str = ""

    img = Image.open(image)
    Thread(target=img.show, daemon=True).start() # TODO (high priority): replace Thread with subprocess
    # That fixes feh capturing stdin and still allows sending a signal to the image viewer (i hope)
    img.show()

    subject_id_context = [{"role": "developer", "content": f"""The user will enter a short prompt, for which you MUST do the following: 
                           If the user prompt describes or matches any of the following subjects: {subjects}, respond '1'.
                           If the user prompt does not describe or match any of the subjects, respond '0'.
                           DO NOTHING ELSE."""}]
    s.conversation_history.append({"role": "developer", "content": f"""
                                   The next image contains the following subjects: {subjects}. 
                                   Start by asking the child what they can see in the image; their response should match one of the above subjects.
                                   If not, gently prompt them by describing a randomly picked subject.
                                   """})
    robot_speech = s.get_llm_response()
    logging.info(f"Robot speech: {robot_speech}")

    
    while num_described < round(num_subjects*0.51) and num_turns < 10:
        human_answer = yield input("Enter human response: ") if settings.debug else s.say_and_listen(robot_speech)

        # TEST (medium priority): the conversational llm and the subject_id llm might not agree which could cause bugs.
        try:
            if int(s.get_custom_llm_response(subject_id_context, human_answer)) == 1: 
                num_described += 1 
        except Exception as e:
            logging.warning("LLM returned unparsable response.")
            logging.info(e)
        num_turns += 1
        # don't get a fresh response for the last turn of the conversation, as we want to insert a new prompt before that.
        if num_described < round(num_subjects*0.51) and num_turns < 10: 
            robot_speech = s.get_llm_response(human_answer)

    s.conversation_history.append({"role": "developer", "content": f"""
                                   That's it for this guessing game! Acknowledge the user's last prompt, then tell them we'll be moving on for now. 
                                   Keep your response short (two sentences MAX) but friendly.
                                   """})
    robot_speech = s.get_llm_response(human_answer)

    if not settings.debug:
        yield s.say(robot_speech)

    img.close()


@inlineCallbacks
def run(s: SessionWrapper):
    """Models an image recognition game the robot can play with the child.

    Will display ann image on the laptop screen, after which the robot will walk the child through describing the image.

    :param s: session object
    """
    prompt = {"role": "developer", 
                "content": f"""
                You are a friendly robot companion talking to a child with Developmental Language Disorder (DLD).
                The child has difficulty understanding complex sentences and finding the right words to say.

                The following is contextual information for the child you are interacting with: {s.human_context}
                The child may be more or less expressive, as indicated by the context; adjust accordingly.

                You will going to be playing a small language game with the child, consisting of a number of rounds, each of which follows this format:
                1. The image will contain a variable number of subjects. The goal is for the child to identify and describe at least SOME of these subjects.
                2. Your job is to prompt the child to do so, without being pushy; if the child can't/won't describe a specific subject, move on to another (pick randomly) after 2-3 conversational turns.
                3. After the child successfully describes/matches a subject, move on to another and prompt them if they see anything else.
                4. Additionally, the conversation is limited to 10 turns in total; keep this in mind.
                """}

    # introduce the game
    s.conversation_history.append({"role": "developer", "content": f"""
                                   First introduce the game to the child; explain in a few short sentences that we will be playing an image guessing game,
                                   and include that we'll be playing {s.language_level} rounds.
                                   """})
    robot_speech = s.get_llm_response()

    if not settings.debug:
        s.say(robot_speech)

    for i in range(0, s.language_level):
        s.conversation_history = []
        s.conversation_history.append(prompt)
        img_file, img_description, num_subjects = key[i]
        single_round(s, "assets/"+img_file, img_description, num_subjects)

    human_answer = yield input("Enter human response: ") if settings.debug else s.listen()
    s.conversation_history.append({"role": "user", "content": human_answer})

    # Respond to the last answer so the conversation doesn't end abruptly.
    s.conversation_history.append({"role": "developer", 
                "content": f"""That's it for this game. Acknowledge the child's last response, then tell them we're moving on for now."""})

    robot_speech = s.get_llm_response()

    if not settings.debug:
        s.say(robot_speech)
        yield s.session.call("rom.optional.behavior.play", name="BlocklyCrouch")
        s.session.leave()
