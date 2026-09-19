from main import ask_with_context

history=[]
answer,note = ask_with_context("How do plants get energy?", history)
print("Answer:", answer)
print("Used note:", note)