# Web Interaction Feature

## Overview

The Web Interaction feature provides a suite of services for interacting with the World Wide Web. It enables the application to perform Google searches, crawl web pages to extract content, and orchestrate these actions to gather information based on search queries.

This feature is designed to be a foundational component, offering building blocks for more complex information retrieval and processing workflows within the main application.

## Core Capabilities

1.  **Google Search Service:** Performs targeted Google searches and returns structured results.
2.  **Web Crawling Service:** Fetches and extracts textual content (in Markdown) and titles from specified URLs.
3.  **Search-Then-Crawl Orchestration:** Combines search and crawl capabilities to retrieve content relevant to a given query.

## Configuration

This feature utilizes the following configurations:

*   **Google API Credentials (Sourced from Core Configuration via `.env` or OS Environment Variables):**
    *   `GOOGLE_API_KEY`: Your Google Cloud API Key with the Custom Search API enabled.
    *   `GOOGLE_CSE_ID`: Your Google Custom Search Engine ID.
*   **Operational Parameters (Defined in `app/features/web_interaction/config.py`):**
    *   `DEFAULT_NUM_GOOGLE_RESULTS`: Default number of results for Google Search (default: 5).
    *   `DEFAULT_NUM_RESULTS_TO_CRAWL`: Default number of search results to crawl in the search-then-crawl operation (default: 3).
    *   `CRAWL_TIMEOUT_SECONDS`: Timeout for a single web crawl operation (default: 60 seconds).
    *   `MAX_CRAWL_CONTENT_LENGTH`: Maximum characters of content to extract from a crawled page before truncation (default: 100,000).

## API Endpoints

All endpoints for this feature are prefixed with `/api/v1/web`. For detailed request/response schemas and status codes, please refer to the API documentation at `/docs`.

---

### 1. Google Search Service

**Endpoint:** `POST /api/v1/web/search`

**Purpose:**
To perform a Google search based on a user-provided query and retrieve a list of relevant web pages. This is useful for discovering information or finding source URLs for further processing.

**Request Body Fields:**
*   `query` (string, required): The search term or question.
*   `num_results` (integer, optional): The desired number of search results to return (typically 1-10). Defaults to the value in `DEFAULT_NUM_GOOGLE_RESULTS`.

**Example Use Case:**
A user wants to find recent articles about "AI in healthcare." This endpoint can be called with the query to get a list of relevant URLs.

---

### 2. Web Crawling Service

#### a. Crawl Single URL

**Endpoint:** `POST /api/v1/web/crawl/single-url`

**Purpose:**
To fetch the main textual content and title from a single, specific web page. This is used when you have a known URL and need its content for analysis, summarization, or indexing.

**Request Body Fields:**
*   `url` (string, HttpUrl, required): The fully qualified URL of the web page to crawl.

**Example Use Case:**
After obtaining a URL from the Google Search Service, this endpoint can be used to retrieve the full content of that specific article.

#### b. Crawl Multiple URLs

**Endpoint:** `POST /api/v1/web/crawl/multiple-urls`

**Purpose:**
To efficiently fetch the main textual content and titles from a list of web pages. This is useful for batch processing multiple URLs, for instance, all links from an RSS feed or a list of bookmarks.

**Request Body Fields:**
*   `urls` (list of strings [HttpUrl], required): A list containing one or more fully qualified URLs to crawl.

**Example Use Case:**
Processing a curated list of industry news websites to extract articles published on a certain day.

---

### 3. Search-Then-Crawl Orchestration Service

**Endpoint:** `POST /api/v1/web/search-and-crawl-results`

**Purpose:**
To automate the common workflow of searching for information on a topic and then immediately retrieving the content of the most relevant search results. This provides a direct way to get textual content related to a query without multiple API calls.

**Request Body Fields:**
*   `query` (string, required): The search term or question.
*   `num_search_results_to_crawl` (integer, optional): The number of top Google search results whose content should be fetched. Defaults to the value in `DEFAULT_NUM_RESULTS_TO_CRAWL`.

**Example Use Case:**
A user asks a question like "What are the main challenges of adopting electric vehicles?" This endpoint can search for relevant articles and return their content directly for use in an LLM prompt or for summarization.

---
