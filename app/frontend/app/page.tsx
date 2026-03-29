'use client';
import { useState, useEffect } from 'react';
import { fetchTodayNews, runPipeline, fetchDigest, NewsArticle } from '@/lib/api';

export default function AnalystDashboard() {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [digestHtml, setDigestHtml] = useState("");
  const [loading, setLoading] = useState(false);
  
  // --- Profile State ---
  const [profile, setProfile] = useState({
    name: "Krish",
    bio: "Macroeconomic and Political Analyst focusing on global market trends...",
    interests: ["Global Markets", "Fiscal Policy"],
    mustInclude: ["Inflation", "Interest Rates"]
  });

  useEffect(() => {
    refreshData();
  }, []);

  const refreshData = async () => {
    const [news, digest] = await Promise.all([fetchTodayNews(), fetchDigest()]);
    setArticles(news);
    setDigestHtml(digest.html);
  };

  const handleSyncProfile = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/profile/suggest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: profile.name, bio: profile.bio }),
      });
      const suggested = await res.json();
      setProfile({
        ...profile,
        interests: suggested.interests,
        mustInclude: suggested.must_include
      });
      alert("AI has suggested new interests based on your bio!");
    } finally {
      setLoading(false);
    }
  };

  const handleStartMission = async () => {
    setLoading(true);
    await runPipeline();
    alert("Analyst Agents Dispatched!");
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-[#0f172a] text-slate-200 p-6 font-sans">
      <header className="flex justify-between items-center mb-8 border-b border-slate-700 pb-6">
        <div>
          <h1 className="text-3xl font-extrabold bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">ANALYST HUB</h1>
          <p className="text-slate-400 text-xs mt-1 uppercase tracking-widest font-semibold">Macro-Political Intelligence</p>
        </div>
        <button 
          onClick={handleStartMission}
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-500 text-white font-bold py-2 px-8 rounded shadow-lg transition-all"
        >
          {loading ? "EXECUTING MISSION..." : "RUN DAILY MISSION"}
        </button>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 h-[calc(100vh-180px)]">
        
        {/* LEFT COLUMN: Profile Setup */}
        <div className="lg:col-span-3 flex flex-col gap-4 bg-slate-900/50 p-6 rounded-xl border border-slate-800">
          <h2 className="text-sm font-bold text-blue-400 uppercase tracking-widest">Profile Setup</h2>
          
          <div className="space-y-4">
            <div>
              <label className="text-[10px] text-slate-500 uppercase font-bold">Your Name</label>
              <input 
                className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-sm mt-1 focus:border-blue-500 outline-none"
                value={profile.name}
                onChange={(e) => setProfile({...profile, name: e.target.value})}
              />
            </div>
            
            <div>
              <label className="text-[10px] text-slate-500 uppercase font-bold">Professional Bio</label>
              <textarea 
                className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-xs mt-1 h-32 focus:border-blue-500 outline-none"
                value={profile.bio}
                onChange={(e) => setProfile({...profile, bio: e.target.value})}
              />
            </div>

            <button 
              onClick={handleSyncProfile}
              className="w-full bg-slate-700 hover:bg-slate-600 text-xs font-bold py-2 rounded transition-colors"
            >
              ✨ SYNC INTERESTS VIA AI
            </button>

            <div className="pt-4">
              <label className="text-[10px] text-slate-500 uppercase font-bold">Active Interests</label>
              <div className="flex flex-wrap gap-2 mt-2">
                {profile.interests.map(i => (
                  <span key={i} className="text-[10px] bg-blue-900/30 text-blue-400 px-2 py-1 rounded border border-blue-800/50">{i}</span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* MIDDLE COLUMN: News Feed */}
        <div className="lg:col-span-4 flex flex-col gap-4 overflow-y-auto pr-2 custom-scrollbar">
          <h2 className="text-sm font-bold text-slate-500 uppercase tracking-widest">Priority Signals</h2>
          {articles.map((art) => (
            <div key={art.id} className="bg-slate-800/40 border border-slate-700 p-4 rounded-lg">
              <div className="flex justify-between items-center mb-2">
                <span className="text-blue-400 text-[10px] font-bold px-2 py-0.5 rounded border border-blue-800">SCORE: {art.impact_score}</span>
              </div>
              <h3 className="font-bold text-sm text-slate-100 mb-1">{art.article_name}</h3>
              <p className="text-xs text-slate-400 line-clamp-2 italic">"{art.summary}"</p>
            </div>
          ))}
        </div>

        {/* RIGHT COLUMN: Digest View */}
        <div className="lg:col-span-5 bg-white rounded shadow-2xl overflow-hidden flex flex-col border border-slate-700">
          <div className="bg-slate-50 p-2 border-b border-slate-200 flex justify-between items-center">
            <span className="text-slate-900 font-bold text-[10px] uppercase">Daily Briefing</span>
            <button onClick={refreshData} className="text-blue-600 text-[10px] font-bold">REFRESH</button>
          </div>
          <iframe 
            srcDoc={digestHtml} 
            className="w-full flex-grow border-none"
            title="Narrative Digest"
          />
        </div>

      </div>
    </div>
  );
}