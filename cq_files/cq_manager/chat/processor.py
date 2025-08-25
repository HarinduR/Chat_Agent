# cq_manager/chat/processor.py
import os
import re
import uuid
from typing import Tuple

from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA

from cq_files.cq_manager.chat.document_processor import DocumentProcessor
from cq_files.cq_manager.chat.llm_handler import LLMHandler
from cq_files.cq_manager.config import Config


class ChatProcessor:
    def __init__(self):
        self.doc_processor = DocumentProcessor(
            knowledge_base_path=os.getenv(
                "KNOWLEDGE_BASE_PATH", Config.KNOWLEDGE_BASE_PATH
            ),
            vector_store_path=os.getenv("VECTOR_STORE_PATH", Config.VECTOR_STORE_PATH),
        )
        self.llm_handler = LLMHandler()
        self.vector_store = self.initialize_vector_store()
        self.qa_chain = self.setup_qa_chain()

    def initialize_vector_store(self):
        vs = self.doc_processor.load_vector_store()
        if not vs:
            print("Vector store missing; creating a new one...")
            vs = self.doc_processor.process_and_store()
        else:
            print("Vector store loaded")
        return vs

    def setup_qa_chain(self):
        prompt_template = """You are a waste management assistant.
                             Use the context to answer.
                            
                             Context: {context}
                             Question: {question}
                            
                             Guidelines:
                             - Provide ONLY the specific information requested
                             - 20–70 words
                             - Clear, complete sentences
                             - No introductions or filler
                             - Be conversational
                             - Start with the direct answer
                             - Include contact info ONLY if explicitly requested
                             - For collection schedules, state the specific day/time only
                             - No quotes around the answer
                             """
        PROMPT = PromptTemplate(
            template=prompt_template, input_variables=["context", "question"]
        )
        return RetrievalQA.from_chain_type(
            llm=self.llm_handler.llm,
            chain_type="stuff",
            retriever=self.vector_store.as_retriever(search_kwargs={"k": 3}),
            chain_type_kwargs={"prompt": PROMPT},
        )

    # ------------------------
    # Heuristic + LLM Intents
    # ------------------------
    def classify_intent(self, message: str, session_id: str) -> Tuple[str, float]:
        # quick heuristic first
        if self._is_greeting(message):
            return "Greetings", 0.9
        if self._is_thanks(message):
            return "Feedback", 0.8
        if self._is_complaint(message):
            return "Complaints", 0.8
        if self._is_schedule_query(message):
            return "Waste Collection Schedules", 0.8

        prompt = f"""
                 Classify this message into EXACTLY one category:
                 - Complaints
                 - Feedback
                 - 3R Tips
                 - Public Awareness Tips
                 - Waste Collection Schedules
                 - Greetings
                 - Unknown
                
                 Message: "{message}"
                
                 Return JSON: {{"intent":"<one of above>","confidence":<0..1>}}
                 """
        try:
            raw = self.llm_handler.generate_response(prompt)
            # naive parse
            intent = "Unknown"
            conf = 0.6
            m = re.search(r'"intent"\s*:\s*"([^"]+)"', raw)
            if m:
                intent = m.group(1)
            m2 = re.search(r'"confidence"\s*:\s*([0-9]*\.?[0-9]+)', raw)
            if m2:
                conf = float(m2.group(1))
            return intent, conf
        except Exception:
            return "Unknown", 0.5

    # ------------------------
    # Pipeline helpers
    # ------------------------
    def _clean_response(self, response: str) -> str:
        if isinstance(response, str):
            s = response.strip()
            if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
                response = s[1:-1]
        for prefix in [
            "Answer: ",
            "Response: ",
            "Based on the information,",
            "According to the information,",
        ]:
            if response.strip().startswith(prefix):
                response = response[len(prefix):].strip()

        response = re.sub(r'(\*{1,2}|_{1,2}|-{3,}|#{1,6}\s)', '', response)
        response = re.sub(r'^\d+\.\s*|\•\s*|\-\s*', '', response, flags=re.MULTILINE)
        response = re.sub(r'^[\'"]+|[\'"]+$', '', response, flags=re.MULTILINE)
        response = ' '.join(response.split())
        if response:
            response = response[0].upper() + response[1:]
        return response

    def _check_relevance(self, query, document_content):
        query_terms = set(re.findall(r'\b\w{3,}\b', query.lower()))
        doc_terms = set(re.findall(r'\b\w{3,}\b', document_content.lower()))
        overlap = query_terms.intersection(doc_terms)
        waste_keywords = {'waste', 'recycle', 'trash', 'garbage', 'collect', 'bin'}
        important_overlap = overlap.intersection(waste_keywords)
        return len(overlap) >= 2 or len(important_overlap) >= 1

    def _validate_response_completeness(self, response, message):
        if not response.strip().endswith((".", "!", "?")):
            completion_prompt = f"""
                                Original question: "{message}"
                                Incomplete response: "{response}"
                                Finish the response in 1 short sentence, without repeating.
                                """
            try:
                completion = self.llm_handler.generate_response(completion_prompt)
                return self._clean_response(f"{response} {completion}")
            except Exception:
                return response
        return response

    # ------------------------
    # Slot helpers
    # ------------------------
    def get_schedule_from_knowledge_base(self, waste_type=None):
        query = "waste collection schedule"
        if waste_type:
            query = f"{waste_type} waste collection schedule"
        docs = self.vector_store.similarity_search(query, k=5)
        out = []
        for d in docs:
            if "collection" in d.page_content.lower() and "schedule" in d.page_content.lower():
                out.append(d.page_content)
        return "\n".join(out)

    def get_contact_details_from_knowledge_base(self):
        docs = self.vector_store.similarity_search("municipal council contact details", k=5)
        out = []
        for d in docs:
            if any(k in d.page_content.lower() for k in ["contact", "phone", "email", "address"]):
                out.append(d.page_content)
        return "\n".join(out)

    # ------------------------
    # Lightweight classifiers
    # ------------------------
    def _is_schedule_query(self, message):
        kws = ["schedule", "collection", "pickup", "pick up", "collect",
               "garbage day", "trash day", "when", "what day", "what time",
               "organic waste", "inorganic waste", "e-waste"]
        return any(k in message.lower() for k in kws)

    def _is_greeting(self, message):
        greetings = ['hello', 'hi', 'hey', 'greetings', 'howdy',
                     'good morning', 'good afternoon', 'good evening']
        return any(g in message.lower() for g in greetings) and len(message.split()) < 5

    def _is_feedback(self, message):
        kws = ['feedback', 'suggestion', 'improve', 'better', 'thanks',
               'thank you', 'grateful', 'appreciate', 'good job', 'well done',
               'helpful', 'service', 'experience']
        return any(k in message.lower() for k in kws)

    def _is_thanks(self, message):
        kws = ['thanks', 'thank you', 'appreciated', 'grateful', 'appreciate', 'valuable']
        return any(k in message.lower() for k in kws) and len(message.split()) < 7

    def _is_complaint(self, message):
        kws = ['complaint', 'issue', 'problem', 'not working', 'broken', 'failed', 'poor',
               'missed', 'miss', 'disappointed', 'unhappy', 'dissatisfied', 'bad',
               'terrible', 'horrible', "didn't collect", "didn't pick up", 'skipped', 'forgot']
        return any(k in message.lower() for k in kws)

    def _is_contact_request(self, message):
        contact_k = ['contact', 'details', 'phone', 'number', 'email', 'address', 'website', 'office']
        municipal_k = ['municipal', 'council', 'office', 'city', 'town', 'local']
        return any(k in message.lower() for k in contact_k) and any(k in message.lower() for k in municipal_k)

    # ------------------------
    # Main handler
    # ------------------------
    def process_message(self, message: str, session_id: str = None) -> str:
        try:
            session_id = session_id or str(uuid.uuid4())
            intent, confidence = self.classify_intent(message, session_id)

            if self._is_contact_request(message):
                info = self.get_contact_details_from_knowledge_base()
                if info:
                    prompt = f"""
                             User asked: "{message}"
                             Contact information from knowledge base:
                             {info}
                            
                             Provide a clear answer. If they asked email only, give only that. Do NOT hyperlink emails.
                             """
                    return self._clean_response(self.llm_handler.generate_response(prompt))

            if self._is_greeting(message) and len(message.split()) < 5:
                return "Hello! How can I help with waste management today?"

            if self._is_thanks(message):
                return "Thank you! Any other waste management questions?"

            if intent == "Feedback" and self._is_feedback(message):
                return "Thank you for your feedback! Any other waste management questions?"

            if intent == "Complaints" or self._is_complaint(message):
                if any(w in message.lower() for w in ['miss', 'missed', "didn't collect", 'skipped', 'forgot']):
                    complaint_prompt = f"""
                                        Complaint about missed collection: "{message}"
                                        Write 20–60 words that:
                                        1) Apologize
                                        2) Say it's reported to the collection team
                                        3) Assure pickup next scheduled day or sooner
                                        4) Keep professional, empathetic tone
                                        """
                    return self._clean_response(self.llm_handler.generate_response(complaint_prompt))

                # try to find KB-backed solution
                docs = self.vector_store.similarity_search(message, k=5)
                for d in docs:
                    if any(w in d.page_content.lower() for w in ["solution", "resolve", "fix", "address"]):
                        sol_prompt = f"""
                                     Complaint: "{message}"
                                     Relevant info:
                                     {d.page_content}
                                    
                                     Write 20–60 words:
                                     - Acknowledge with empathy
                                     - Provide solution ONLY from the info above
                                     - Brief apology
                                     - Professional tone
                                     """
                        return self._clean_response(self.llm_handler.generate_response(sol_prompt))

                return ("I’m sorry about this issue. I don’t have a specific fix in my KB. "
                        "If you share your contact details, our waste team will reach out to resolve it.")

            # Non-waste queries guard
            if not self.is_waste_management_related(message):
                return ("I’m designed for waste management. Please ask about waste disposal, recycling, "
                        "collection schedules, or sustainability.")

            # Schedule shortcut
            if intent == "Waste Collection Schedules" or self._is_schedule_query(message):
                wtype = None
                ml = message.lower()
                if "organic" in ml: wtype = "organic"
                elif "inorganic" in ml: wtype = "inorganic"
                elif "e-waste" in ml or "electronic" in ml: wtype = "e-waste"

                info = self.get_schedule_from_knowledge_base(wtype)
                if info:
                    prompt = f"""
                             User asked: "{message}"
                             Schedule info:
                             {info}
                            
                             Answer ONLY with concrete day/time if present. Keep it clear.
                             """
                    return self._clean_response(self.llm_handler.generate_response(prompt))

            # Default RAG
            response = self.qa_chain.run(message)
            if len(response.split()) < 10:
                enhance = f"""
                          User asked: "{message}"
                          Initial answer: "{response}"
                          Improve briefly (still concise and helpful).
                          """
                response = self.llm_handler.generate_response(enhance)

            response = self._clean_response(response)
            response = self._validate_response_completeness(response, message)
            return response

        except Exception as e:
            print(f"process_message error: {e}")
            return "I encountered an error. Please try again with your waste management question."

    def is_waste_management_related(self, message: str) -> bool:
        # quick exits
        if self._is_feedback(message) or self._is_greeting(message) or self._is_thanks(message) or self._is_complaint(message):
            return True

        classification_prompt = f"""
                                Is this about waste management / sustainability? 
                                Message: "{message}"
                                Respond ONLY YES or NO.
                                """
        try:
            resp = self.llm_handler.generate_response(classification_prompt).strip().upper()
            return "YES" in resp
        except Exception:
            return True
