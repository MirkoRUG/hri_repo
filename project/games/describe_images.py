from session import SessionWrapper
import settings
import logging
from twisted.internet.defer import inlineCallbacks
import subprocess
import signal
from PIL import Image


# map language level to the image file + metadata
key = {
 0: ('cattle_abduction.jpg', "The image contains a green ufo/alien abducting a cow. There are 3 small sprigs/grass/plants visible.", 3),
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

    # if-elif for non-linux distributions cause Linux is my specialest little operating system
    if settings.os == "Linux":
        # Not how i'd like to do this in an ideal scenario (that would be PIL.Image.open()), but this is the one way on linux i've found that 
        # 1) does not have feh capture stdin input
        # 2) listens to SIGTERM
        process = subprocess.Popen(["feh", "-f-"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        process.stdin.write(image)
        process.stdin.close()
    else:
        img = Image.open(image)
        img.show()


    subject_id_context = [{"role": "developer", "content": f"""You are being used to classify whether the user correctly identified ONE OR more subjects in an image.
                            For each prompt, do the following:
                            IF the user identifies ANY ONE OR MORE of these components: "{subjects}", RESPOND WITH '1; <reasoning>'.
                            IF the user does not describe or match ANY of these components: "{subjects}", RESPOND WITH '0; <reasoning>'.
                            PARTIAL MATCHES (the user identifying only one part of the image) ARE ACCEPTABLE AND SHOULD RETURN a'1'!!!
                            MAKE SURE TO LOOK FOR **SEMANTIC** MATCHES, not synctactic ones. 
                            If the user says something slightly nonsensical that may resonable be extrapolated as indicating any of the subjects, accept this is a a valid match. Example: the user says 'ali', which could mean 'alien' and should thus match if 'alien' is in the subjects.
                            """}]
    s.conversation_history.append({"role": "developer", "content": f"""
                                   The next image contains the following subjects: {subjects}. 
                                   Start by asking the child what they can see in the image; their response should match one of the above subjects.
                                   If not, gently prompt them by describing a randomly picked subject.
                                   """})
    robot_speech = s.get_llm_response()
    logging.info(f"Robot speech: {robot_speech}")

    
    while num_described < round(num_subjects*0.51) and num_turns < 10:
        human_answer = yield input("Enter human response: ") if settings.debug else s.say_and_listen(robot_speech)

        try:
            # note: with this setup the model holding the conversation and the model identifying subjects don't necessarily have to agree on the child's response
            # This didn't cause any issues during testing, so imo it's fine
            rsp = s.get_custom_llm_response(subject_id_context, human_answer)
            logging.info(f"custom LLM response: {rsp}")
            if int(rsp.split(';')[0]) == 1: 
                num_described += 1 
        except Exception as e:
            logging.warning("LLM returned unparsable response.")
            logging.info(e)
        num_turns += 1

        # don't get a fresh response for the last turn of the conversation, as we want to insert a new prompt before that.
        if num_described < round(num_subjects*0.51) and num_turns < 10: 
            robot_speech = s.get_llm_response(human_answer)
            logging.info(f"Robot speech: {robot_speech}")


    s.conversation_history.append({"role": "developer", "content": f"""
                                   That's it for this guessing game! Acknowledge the user's last prompt, then tell them we'll be moving on for now. 
                                   Keep your response short (two sentences MAX) but friendly.
                                   """})
    robot_speech = s.get_llm_response(human_answer)
    logging.info(f"Robot speech: {robot_speech}")

    if not settings.debug:
        yield s.say(robot_speech)

    if settings.os == "Linux":
        process.send_signal(signal.SIGTERM)
        process.wait()
    else:
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
                2. Your job is to prompt the child to do so, without being pushy; if the child can't/won't describe a specific subject, move on to another (pick randomly) after 1-2 conversational turns.
                3. After the child successfully describes/matches a subject, move on to another and prompt them if they see anything else.
                4. A different llm **already had** a short introductory conversation with the child, so there is no need for pleasantries or greetings; simply get started with the game immediately. 
                """}

    # introduce the game
    s.conversation_history.append({"role": "developer", "content": f"""
                                   First introduce the game to the child; explain in a few short sentences that we will be playing an image guessing game,
                                   and include that we'll be playing {s.enthousiasm} rounds.
                                   """})
    robot_speech = s.get_llm_response()
    logging.info(f"Robot speech: {robot_speech}")

    if not settings.debug:
        yield s.say(robot_speech)

    for i in range(0, s.enthousiasm):
        s.conversation_history = []
        s.conversation_history.append(prompt)
        img_file, img_description, num_subjects = key[i]
        yield single_round(s, "assets/"+img_file, img_description, num_subjects)

    # Respond to the last answer so the conversation doesn't end abruptly.
    s.conversation_history.append({"role": "developer", 
                "content": f"""That's it for this game. Acknowledge the child's last response, then tell them we're done playing this game."""})

    robot_speech = s.get_llm_response()
    logging.info(f"Robot speech: {robot_speech}")

    if not settings.debug:
        yield s.say(robot_speech)
