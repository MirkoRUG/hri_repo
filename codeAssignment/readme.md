# code assignment
This project models an initial getting-to-know-you conversation between a social robot and a child with developmental language disorder (DLD).
It integrates with an LLM through the OpenAI API.


# Prerequisites
Required packages are included in `requirements.txt`.
Simply set up a virtual environment to install the packages:
```sh
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

# Configuration
Before you can run the program, you must first set some required environment variables.
The program uses a `.env` file to read these variables.

You'll need to provide two variables explicitly, namely an OpenAI API key, and the realm to connect to the robot.  
Once you have these, add them to the env file by first copying the example file, then adding the values:
```sh
cp env.example .env
sed -i 's/openaikeyhere/<your_openai_key>/' .env
sed -i 's/robotrealmhere/<robot_realm>/' .env
```

Optionally you can change the model the program uses by changing the `OPENAI_MODEL` variable.


# Running
Running the program is very straightforward.
```sh
source .venv/bin/activate
uv run main.py
```

The program will go through two conversations with the user, namely:
 1) a turn-limited initial conversation, in which the robot asks the user their name and a few simple questions. 
 2) an open-ended second conversation, where the robot will engage the user about familiar topics; the purpose of this is to get the user comfortable and familiar with the robot.

While the program is running, it will output both the processed user speech and the planned responses by the LLM to stdout for logging. 
