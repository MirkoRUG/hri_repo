from syllables import estimate as n_syllables


class Body:
    """The Body class has all the properties of the robot's body
    It is responsible for sending a list of frames to the robot
    """
    # Raw data: name, min, max, time
    _part_data = [
        ["head_yaw", "body.head.yaw", -0.874, 0.874, 600],
        ["head_roll", "body.head.roll", -0.174, 0.174, 400],
        ["head_pitch", "body.head.pitch", -0.174, 0.174, 400],
        ["arm_R_U", "body.arms.right.upper.pitch", -2.59, 1.59, 1600],
        ["arm_R_L", "body.arms.right.lower.roll", -1.74, 0, 700],
        ["arm_L_U", "body.arms.left.upper.pitch", -2.59, 1.59, 1600],
        ["arm_L_L", "body.arms.left.lower.roll", -1.74, 0, 700],
        ["torso_yaw", "body.torso.yaw", -0.874, 0.874, 1000],
        ["leg_R_U", "body.legs.right.upper.pitch", -1.73, 1.73, 1000],
        ["leg_R_L", "body.legs.right.lower.pitch", -1.5, 1.5, 800],
        ["leg_R_F", "body.legs.right.foot.roll", -0.849, 2.49, 800],
        ["leg_L_U", "body.legs.left.upper.pitch", -1.73, 1.73, 1000],
        ["leg_L_L", "body.legs.left.lower.pitch", -1.5, 1.5, 800],
        ["leg_L_F", "body.legs.left.foot.roll", -0.849, 2.49, 800],
    ]

    # Class dictionaries
    part_name = {p[0]: p[1] for p in _part_data}
    part_min = {p[0]: p[2] for p in _part_data}
    part_max = {p[0]: p[3] for p in _part_data}
    part_time = {p[0]: p[4] for p in _part_data}

    # The stand position was extracted using proprioception
    stand_position = {boy_part:0 for boy_part in part_name.values()}
    stand_position.update({part_name["arm_R_L"]: -0.8726,
                           part_name["arm_R_U"]: 0.023598775598298816,
                           part_name["arm_L_L"]: -0.8726,
                           part_name["arm_L_U"]: 0.023598775598298816,
                           part_name["leg_L_F"]: -0.03161255787892264,
                           part_name["leg_R_U"]: -0.017453292519943295,
                           part_name["leg_L_L"]: -0.017453292519943295,
                           part_name["leg_L_U"]: -0.017453292519943295,
                           part_name["leg_R_F"]: 0.03161255787892264})

    def sentence_time(self, sentence):
        """Time in ms it takes the TTS to read a sentence
        The formula was estimated by timing sample sentence, and adjusted by trial and error"""
        return int(1000*(0.2 + 0.2*n_syllables(sentence) + 0.3 * sentence[:-1].count(".") + 0.3 * sentence[:-1].count(",")))

    def victory_movement(self, sentence):
        """Generate the frames for a victory movement"""
        frames = []
        # search for idx of the iconic word
        iconic_words = ["victory", "congratulations", "win ", "win.", "win!" ]
        for word in iconic_words:
            pos = sentence.find(word)
            if pos != -1:
                break

        #calculate time to reach iconic word
        sentence = sentence[:pos]
        t = self.sentence_time(sentence)-200

        # Do movement in sync with the iconic word
        frames.append({"time": t, "data": Body.stand_position.copy()})
        frames.append({"time": t+400, "data": self.win_position()})
        frames.append({"time": t+800, "data": self.win_position()})
        frames.append({"time": t+1200, "data": Body.stand_position.copy()})
        return frames

    def eating_movement(self, sentence):
        """Generate the frames for an eating movement"""
        # Pantomimic gesture
        frames = []
        # search for idx of the iconic word
        iconic_words = ["eat", "food", "fruit", "drink", "beverage"]
        for word in iconic_words:
            pos = sentence.find(word)
            if pos != -1:
                break

        #calculate time to reach iconic word
        sentence = sentence[:pos]
        t = self.sentence_time(sentence) - 200

        # Do movement in sync with iconic word
        frames.append({"time": t, "data": Body.stand_position.copy()})
        frames.append({"time": t+400, "data": self.eat_position()})
        frames.append({"time": t+700, "data": self.eat_position()})
        frames.append({"time": t+1100, "data": Body.stand_position.copy()})
        return frames

    def beat_movement(self, sentence):
        """Generate the frames for beat movements"""
        frames = []
        t = self.sentence_time(sentence)

        # Three movements: preparation, stroke, retraction. Repeated for as long as the sentence lasts
        for i in range(100, t-800, 2400):
            frames.append({"time": i, "data": Body.stand_position.copy()})
            frames.append({"time": i+800, "data": self.iconic_position()})
            frames.append({"time": i+1600, "data": Body.stand_position.copy()})
        return frames

    def win_position(self):
        """Returns the hand-crafted win position"""
        position = Body.stand_position.copy()
        position.update({Body.part_name["head_pitch"]: Body.part_min["head_pitch"]})
        position.update({Body.part_name["arm_R_U"]: Body.part_min["arm_R_U"]})
        position.update({Body.part_name["arm_L_U"]: Body.part_min["arm_L_U"]})
        position.update({Body.part_name["arm_R_L"]: Body.part_max["arm_R_U"]})
        position.update({Body.part_name["arm_L_L"]: Body.part_max["arm_L_U"]})
        return position

    def eat_position(self):
        """Returns the hand-crafted eat position"""
        position = Body.stand_position.copy()
        position.update({Body.part_name["arm_R_U"]: -2.1})
        position.update({Body.part_name["arm_R_L"]: -1.2})
        position.update({Body.part_name["head_yaw"]: -0.65})
        position.update({Body.part_name["head_pitch"]: Body.part_min["head_pitch"]})
        return position

    def iconic_position(self):
        """Returns the hand-crafted iconic position"""
        position = Body.stand_position.copy()
        position.update({Body.part_name["head_pitch"]: Body.part_min["head_pitch"]})
        position.update({Body.part_name["head_roll"]: Body.part_min["head_roll"]})
        position.update({Body.part_name["arm_R_U"]: -1})
        position.update({Body.part_name["arm_L_U"]: -1})
        position.update({Body.part_name["arm_R_L"]: -1})
        position.update({Body.part_name["arm_L_L"]: -1})
        return position

    def yes_movement(self):
        """Generates frames for a "yes" movement (nodding)"""
        frames = []
        frames.append({"time": 200, "data": self._get_modified_position("head_pitch", 0.174)})
        frames.append({"time": 600, "data": Body.stand_position.copy()})
        frames.append({"time": 1000, "data": self._get_modified_position("head_pitch", 0.174)})
        frames.append({"time": 1400, "data": Body.stand_position.copy()})
        return frames

    def no_movement(self):
        """Generates frames for a "no" movement (shaking head)."""
        frames = []
        frames.append({"time": 200, "data": Body.stand_position.copy()})
        frames.append({"time": 700, "data": self._get_modified_position("head_yaw", 0.51)})
        frames.append({"time": 1200, "data": self._get_modified_position("head_yaw", -0.51)})
        frames.append({"time": 1700, "data": self._get_modified_position("head_yaw", 0.51)})
        frames.append({"time": 2200, "data": Body.stand_position.copy()})
        return frames

    def _get_modified_position(self, part_name, value):
        """Helper function to modify a specific body part from the stand position
        Used only for yes and no gestures"""
        position = Body.stand_position.copy()
        if part_name in self.part_name:
            position[self.part_name[part_name]] = value
        else:
            print(f"Warning: '{part_name}' is not a valid part name.")
        return position
