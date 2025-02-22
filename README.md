# Extended Knowledge repository
Extended knowledge repository is an environment where an organization can organize knowledge about subjects of interest. For each subject we can store documents and extend this knowledge base with hierarchical notes.
Countinuous search and web crawling can enhance the knowledge base with updated insights from internet.

# Objectives 
- Store information of interest in a hierarchical notes
- Enrich notes with content from documents, media and web pages
- Keep notes updates using actualized content from web crawling
- Present summaries, insights, updates
- Provide answer based on collected knowlegde

# Use cases
 the knowledge base can be built to gather and enrich information on any important subject as :
 - Political context Economic war between USA and China
 - Scientific research (Latest breakthroughs inquantum computing)
 - Competitors monitoring (Différent solar panel vendors in MENA région market)

 To start a knowledge base a subject should be developped in a hierachical manner into subtopics. it can be represented like a mindmap.
 
```mermaid
mindmap
  root((Economic war between USA and China))
    sub1((NVIDIA))
      sub1a(Alternatives)
      sub1b(Chinese companies still using NVIDIA)
    sub2((ASML))
      sub2a(marketshare)
      sub2b(advanced lithography)
        sub2b1(Clients)
        sub2b2(endorsment)
    sub3((Lithography))
      sub3a(Huawei)
      sub3b(SMIC)
    sub4((RISC V))
      sub4a(Processors for AI)
 ```

# Tools
- **Database** : Mysql for notes storing mysql but should be independant from DB.
- **Documents indexing** : Elastic search
- **Web crawling** : Crawl4AI
- **Mobile app** : Flutter
