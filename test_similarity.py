from embeddings import get_embedding
import cosine_similarity

vec_a= get_embedding("Photosynthesis converts light into energy")
vec_b= get_embedding("Plants use sunlight to make food")
vec_c= get_embedding("The stock market crashed yesterday")

print("Similar sentences:", cosine_similarity(vec_a, vec_b))
print("Unrelated sentences:", cosine_similarity(vec_a, vec_c))