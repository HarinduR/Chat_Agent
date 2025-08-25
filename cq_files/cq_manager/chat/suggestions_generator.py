# cq_manager/chat/suggestions_generator.py
import os
from cq_files.cq_manager.chat.llm_handler import LLMHandler
from cq_files.cq_manager.chat.document_processor import DocumentProcessor
from cq_files.cq_manager.config import Config


class SuggestionsGenerator:
    def __init__(self):
        self.llm_handler = LLMHandler()
        self.doc_processor = DocumentProcessor(
            knowledge_base_path=os.getenv("KNOWLEDGE_BASE_PATH", Config.KNOWLEDGE_BASE_PATH),
            vector_store_path=os.getenv("VECTOR_STORE_PATH", Config.VECTOR_STORE_PATH),
        )
        self.vector_store = self.doc_processor.load_vector_store()
        if not self.vector_store:
            print("Vector store not found; building...")
            self.vector_store = self.doc_processor.process_and_store()

    def _clean_suggestion(self, s: str) -> str:
        for ch in ['*', '_', '`', '"', "'", '1.', '2.', '3.', '-']:
            s = s.replace(ch, '').strip()
        if not s.endswith('?'):
            s += '?'
        return s

    def _is_valid_suggestion(self, s: str) -> bool:
        s_low = s.lower()
        is_q = '?' in s
        is_3r = any(t in s_low for t in [
            'reduce', 'reuse', 'recycle', 'waste', 'trash', 'garbage',
            'compost', 'environment', 'sustainable', 'eco', 'green',
            'plastic', 'paper', 'glass', 'metal', 'organic'
        ])
        return is_q and is_3r and len(s.split()) <= 12

    def _generate_default_3r_suggestions(self, count: int):
        fallback = [
            "How can I reduce food waste at home?",
            "Which plastics can I recycle locally?",
            "Can I reuse glass jars for storage?",
            "Any tips for composting kitchen scraps?",
            "How do I cut daily plastic use?",
        ]
        return fallback[:count]

    def generate_suggestions(self, user_input: str, bot_response: str, max_suggestions: int = 3):
        reduce_docs = self.vector_store.similarity_search("reduce waste tips advice", k=3)
        reuse_docs = self.vector_store.similarity_search("reuse items tips advice", k=3)
        recycle_docs = self.vector_store.similarity_search("recycling tips advice", k=3)

        kb = "\n".join(d.page_content for d in (reduce_docs + reuse_docs + recycle_docs))

        prompt = f"""
                 You are a waste management assistant specializing in 3R tips.
                
                 Conversation:
                 User: {user_input}
                 Assistant: {bot_response}
                
                 Knowledge base:
                 {kb}
                
                 Generate exactly {max_suggestions} actionable follow-up questions (under 10 words each), 
                 each clearly about Reduce, Reuse or Recycle. Base them ONLY on the knowledge above.
                 One line per question. No numbering or formatting.
                 """
        try:
            raw = self.llm_handler.generate_response(prompt)
            suggestions = [self._clean_suggestion(x.strip()) for x in raw.splitlines() if x.strip()]
            suggestions = [s for s in suggestions if self._is_valid_suggestion(s)]
            if len(suggestions) < max_suggestions:
                suggestions += self._generate_default_3r_suggestions(max_suggestions - len(suggestions))
            return suggestions[:max_suggestions]
        except Exception as e:
            print(f"Suggestions error: {e}")
            return self._generate_default_3r_suggestions(max_suggestions)
