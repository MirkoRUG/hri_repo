# Social Robot Language Learning Demo

This project is a demo of a social robot designed to personalize language learning over time for children with Developmental Language Disorder (DLD).

## Key files

- `main.py` - session driver that runs pleasantries, games and wrap-up.
- `session.py` - manages personalization, conversation history, child profile, emotion recognition and robot setup.
- `conversations/pleasantries.py` - opening social conversation that gathers context and readiness.
- `conversations/wrapup.py` - final interaction to close the session positively.
- `games/games.py` - chooses the game based on estimated language level.
- `games/describe_images.py` - image-description game for early language levels.
- `games/twenty_questions.py` - yes/no guessing game.
- `games/description.py` - word-guessing clue game.
- `games/storytelling.py` - collaborative storytelling game for more advanced learners.
- `body.py` - gesture and motion generation for the robot.
- `settings.py` - environment and OpenAI client configuration.

## Requirements

### Python

- Python 3.12 or later

### Dependencies

This project uses the dependencies defined in `pyproject.toml`, including but not limited to:

- `alpha-mini-rug`
- `autobahn`
- `twisted`
- `openai`
- `deepface`
- `opencv-python`
- `pillow`
- `python-dotenv`
- `syllables`
- `tf-keras`
- `numpy`
- `httpx`

### Environment variables

Create a `.env` file in `project/` (or copy `project/env.example`) and define:

- `OPENAI_API_KEY` - your OpenAI API key
- `REALM` - WAMP realm for the robot connection
- `OPENAI_MODEL` - the OpenAI model to use (default in example: `gpt-4o-mini`)
- `DEBUG` - `False` for robot mode, `True` for local debugging

Example:

```
OPENAI_API_KEY="openaikeyhere"
REALM="robotrealmhere"
OPENAI_MODEL="gpt-4o-mini"
DEBUG=False
```

## Setup

1. Create and activate a Python 3.12+ virtual environment.

  ```sh
  cd /path/to/hri_repo/project
  uv venv
  source .venv/bin/activate
  ```

2. Install dependencies.

  ```sh
  uv pip install .
  ```

3. Create a `.env` file in `project/` with the required variables.

  ```sh
  cp env.example .env
  ```
  then edit .env and replace the placeholder values.

4. Add a child profile file in `project/data`, for example `alex.md`.

## Running the demo

### Debug mode

Use debug mode to run locally with text input instead of robot hardware. Set `DEBUG=True`.

### Robot mode

Set `DEBUG=False`.

### Run Command

```sh
uv run python main.py
```

The demo will:

1. initialize the robot session and optional audio/vision services,
2. run the `pleasantries` conversation,
3. choose and play an adaptive language game,
4. run the `wrapup` conversation,
5. update and save personalization data.

## How personalization works

- The child’s profile context is loaded from `data/<name>.md`.
- The robot uses that context to ask more familiar, accessible questions during the opening interaction.
- The system counts the child’s words and assigns a language level.
- A game is selected based on that level:
  - Level 1 - twenty questions
  - Level 2 - word guessing / description 
  - Level 3 - image description
  - Level 4 - storytelling
- After the session, the robot generates an updated profile from the latest conversation and saves it to `data/<name>-convo.md`.
