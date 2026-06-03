from session import SessionWrapper

# TODO (medium priority): add encouragement/praise/reflection on today's session to this function
def wrapup(s: SessionWrapper):
    yield s.session.call("rie.dialogue.stt.close")
    yield s.session.call("rie.dialogue.say_animated", text="Goodbye.")
    yield s.session.call("rom.optional.behavior.play", name="BlocklyCrouch")
    s.session.leave()
