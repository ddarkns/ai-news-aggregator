const API_BASE = "http://localhost:8000";

export interface NewsArticle {
  id: number;
  article_name: string;
  summary: string;
  impact_score: number;
  relevance_explanation: string;
  source_link: string;
}

export const runPipeline = async (query: string = "", topN: number = 1) => {
  const res = await fetch(`${API_BASE}/run-pipeline`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_query: query, top_n: topN }),
  });
  return res.json();
};

export const fetchTodayNews = async (): Promise<NewsArticle[]> => {
  const res = await fetch(`${API_BASE}/news/today`, { cache: 'no-store' });
  if (!res.ok) return [];
  return res.json();
};

export const fetchDigest = async () => {
  const res = await fetch(`${API_BASE}/news/digest`, { cache: 'no-store' });
  return res.json();
};