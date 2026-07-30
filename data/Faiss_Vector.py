from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import CharacterTextSplitter
import os 


folder_path = r"source"
documents = []
for filename in os.listdir(folder_path):
    if filename.endswith(".txt"):
        file_path = os.path.join(folder_path, filename)
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            documents.append(content)

text_spliter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=30)
docs = text_spliter.create_documents(documents)

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

db = FAISS.from_documents(docs, embeddings)
db 

#querying = mencari dokumen yang mirip dengan query yang diberikan
query = "apa itu waifu?"
docs = db.similarity_search(query)
print(docs[0].page_content)


#retrieving = mengambil dokumen yang mirip dengan query yang diberikan
retriver = db.as_retriever()
docs = retriver.get_relevant_documents(query)
print(docs[0].page_content)


#similarity_search_with_score = mencari dokumen yang mirip dengan query yang diberikan dan memberikan skor kemiripan
docs = db.similarity_search_with_score(query)
for doc, score in docs:
    print(f"Score: {score}")
    print(doc.page_content)
    print("\n")


embeding_vector = embeddings.embed_query(query)
print(embeding_vector)

docs_score = db.similarity_search_with_score(query)
for doc, score in docs_score:
    print(f"Score: {score}")
    print(doc.page_content)
    print("\n")