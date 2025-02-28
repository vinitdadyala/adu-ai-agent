# pip install dspy-ai python-dotenv
import os
import dspy
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure DSPy to use Groq with Llama3.3
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY not found in environment variables")

# Set up the Groq LLM with Llama3.3
llm = dspy.LM(
    model="groq/llama-3.3-70b-versatile",
    api_key=groq_api_key,  # Using Llama3.3 70B model
)

# Set the LLM as the default for DSPy
dspy.settings.configure(lm=llm)


# Define a simple DSPy Signature for question answering
class BasicQA(dspy.Signature):
    """Answer questions with short factoid answers."""
    question = dspy.InputField()
    answer = dspy.OutputField(desc="often between 5 and 7 words")

# Pass the signature to the ChainOfThought module
generate_answer = dspy.ChainOfThought(BasicQA)

# Call the predictor on a particular input
question = "What is the color of the sky?"
pred = generate_answer(question=question)

print(f"Question: {question}")
print(f"Predicted Answer: {pred.answer}")