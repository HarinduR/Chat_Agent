# CQ_Manager_Agent/chat/document_processor.py
import os
from typing import List, Optional

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS


class DocumentProcessor:
    def __init__(self, knowledge_base_path: str, vector_store_path: str):
        self.knowledge_base_path = knowledge_base_path
        self.vector_store_path = vector_store_path
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-mpnet-base-v2"
        )

    def load_documents(self):
        print(f"[DocumentProcessor] Loading from {self.knowledge_base_path}")
        if not os.path.exists(self.knowledge_base_path):
            print(f"Error: {self.knowledge_base_path} does not exist")
            return []

        try:
            loader = DirectoryLoader(
                self.knowledge_base_path,
                glob="**/*.txt",
                loader_cls=TextLoader,
                loader_kwargs={"encoding": "utf-8", "autodetect_encoding": True},
                recursive=True,
                silent_errors=False,
                show_progress=True,
            )
            documents = loader.load()
            print(f"Loaded {len(documents)} documents")
        except Exception as e:
            print(f"DirectoryLoader error: {e}")
            # Fallback to a known file if present
            fallback = os.path.join(self.knowledge_base_path, "waste_guidelines.txt")
            documents = []
            if os.path.exists(fallback):
                try:
                    documents = TextLoader(
                        fallback, encoding="utf-8", autodetect_encoding=True
                    ).load()
                    print(f"Manually loaded {len(documents)} doc(s) from {fallback}")
                except Exception as me:
                    print(f"Manual load failed: {me}")

        for i, doc in enumerate(documents[:5]):
            print(f"Doc {i+1} preview: {doc.page_content[:100]}...")

        return documents

    def split_documents(self, documents):
        if not documents:
            return []
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500, chunk_overlap=100, length_function=len
        )
        splits = splitter.split_documents(documents)
        print(f"Created {len(splits)} splits")
        return splits

    def create_vector_store(self, splits):
        if not splits:
            print("No splits to index")
            return None
        print("Creating FAISS vector store...")
        vs = FAISS.from_documents(splits, self.embeddings)
        os.makedirs(self.vector_store_path, exist_ok=True)
        vs.save_local(self.vector_store_path)  # writes index.faiss + index.pkl
        print(f"Saved FAISS to {self.vector_store_path}")
        return vs

    def load_vector_store(self) -> Optional[FAISS]:
        index_path = os.path.join(self.vector_store_path, "index.faiss")
        store_path = os.path.join(self.vector_store_path, "index.pkl")
        if os.path.exists(index_path) and os.path.exists(store_path):
            print(f"Loading FAISS from {self.vector_store_path}")
            try:
                return FAISS.load_local(
                    self.vector_store_path,
                    self.embeddings,
                    allow_dangerous_deserialization=True,
                )
            except Exception as e:
                print(f"FAISS load error: {e}")
        else:
            print("FAISS index not found; will create new")
        return None

    def process_and_store(self):
        docs = self.load_documents()
        if not docs:
            print("No documents found")
            return None
        splits = self.split_documents(docs)
        if not splits:
            print("No splits created")
            return None
        return self.create_vector_store(splits)

    def rebuild_vector_store(self):
        print("Rebuilding FAISS from scratch...")
        docs = self.load_documents()
        splits = self.split_documents(docs)
        return self.create_vector_store(splits)
