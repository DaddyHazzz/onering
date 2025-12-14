# backend/agents/viral_thread.py
"""
LangGraph multi-agent chain for generating viral Twitter threads.
Combines Researcher → Writer → Optimizer agents.
Uses pgvector for retrieving similar past threads as context.
"""
import os
from typing import TypedDict, List, Optional
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END
import logging

logger = logging.getLogger("onering")

# Initialize Groq LLM
groq_api_key = os.getenv("GROQ_API_KEY")
llm = ChatGroq(temperature=0.9, model_name="llama-3.1-8b-instant", api_key=groq_api_key)


class ThreadState(TypedDict):
    """State for viral thread generation."""
    topic: str
    research: str
    draft: str
    final_thread: List[str]
    user_id: Optional[str]
    similar_threads: Optional[List[str]]


def get_similar_past_threads(user_id: Optional[str]) -> List[str]:
    """
    Retrieve similar past threads from pgvector for context.
    In production, this would query pgvector similarity.
    For now, return mock examples.

    Args:
        user_id: Clerk user ID

    Returns:
        List of past thread examples (concatenated tweets)
    """
    if not user_id:
        return []

    try:
        # Mock: Return example viral threads from the user's history
        # In production, this would:
        # 1. Embed current topic using embedThread()
        # 2. Query: SELECT id, content FROM posts WHERE userId = user_id
        #    AND content <-> topic_vector < 0.3 (cosine distance)
        # 3. Limit to top 2-3 most similar
        # 4. Concatenate tweets

        logger.info(f"[researcher] retrieving past threads for user {user_id}")

        # Stub: return empty for now (production would query pgvector)
        return []
    except Exception as e:
        logger.error(f"[researcher] error retrieving past threads: {e}")
        return []


def researcher_agent(state: ThreadState) -> ThreadState:
    """
    Researcher agent: identifies viral trends and angles for the given topic.
    Uses pgvector to retrieve similar past successful threads as context.
    Returns research insights and potential viral angles.
    """
    topic = state.get("topic", "")
    user_id = state.get("user_id")

    # Retrieve similar past threads for context
    similar_threads = get_similar_past_threads(user_id)
    state["similar_threads"] = similar_threads

    context = ""
    if similar_threads:
        context = f"\n\nPast successful threads for reference:\n{chr(10).join(similar_threads[:2])}"

    prompt = f"""You are a viral content researcher. Given the topic: "{topic}"{context}

Provide 2-3 viral angles or trends related to this topic that would resonate on X/Twitter in 2025.
Focus on: controversy, personal story, contrarian takes, or timely insights.
Be concise but specific.

Format:
- Angle 1: [description]
- Angle 2: [description]
- Key insight: [one sentence]"""

    message = HumanMessage(content=prompt)
    response = llm.invoke([message])

    state["research"] = response.content
    logger.info(f"[researcher] generated research for topic: {topic[:50]}...")
    return state


def writer_agent(state: ThreadState) -> ThreadState:
    """
    Writer agent: generates a full viral thread draft using proven 2025 format.
    Format: Hook → Value List → CTA
    CRITICAL: Output MUST have NO numbers, NO prefixes, NO "1/X" EVER.
    Also: Redirect harmful self-talk to motivation.
    """
    topic = state.get("topic", "")
    research = state.get("research", "")

    # Check for self-harm language and redirect
    harmful_keywords = ["worthless", "piece of shit", "kill myself", "useless", "hate myself", "fuck up", "loser", "stupid"]
    if any(keyword in topic.lower() for keyword in harmful_keywords):
        logger.info(f"[writer] detected self-harmful content, redirecting to motivation")
        topic_override = f"Turning self-doubt into fuel: {topic}. Let's create a thread about growth, resilience, and finding strength."
    else:
        topic_override = topic

    prompt = f"""You are an elite X thread writer in 2025. Create a viral 4-7 tweet thread for:
Topic: {topic_override}
Research: {research}

!!!ABSOLUTE CRITICAL RULE!!!
DO NOT OUTPUT ANYTHING LIKE:
- 1/6, 2/6, 3/6 (NO THREAD COUNTERS)
- 1. tweet, 2. tweet (NO DOT NUMBERING)
- (1) tweet, (2) tweet (NO PARENTHESIS NUMBERING)  
- Tweet 1, Tweet 2 (NO WORD NUMBERING)
- [1], [2] (NO BRACKET NUMBERING)
ANY NUMBERING = INSTANT FAIL

OUTPUT FORMAT:
Raw tweet text separated by EXACTLY two newlines (\n\n). NOTHING ELSE.

Example:
First tweet here with energy and no numbers

Second tweet continues the story no numbers

Third tweet wraps up the thread no numbers

NOW GENERATE:"""

    message = HumanMessage(content=prompt)
    response = llm.invoke([message])

    state["draft"] = response.content
    logger.info(f"[writer] drafted thread with {len(response.content)} chars")
    return state


def optimizer_agent(state: ThreadState) -> ThreadState:
    """
    Optimizer agent: refines the thread for maximum engagement.
    Adds emojis, improves line breaks, checks flow.
    CRITICAL: Remove ALL numbering, output tweets separated by \n\n ONLY.
    """
    draft = state.get("draft", "")

    prompt = f"""You are a viral content optimizer. Optimize for maximum engagement.

DRAFT TO OPTIMIZE:
{draft}

MANDATORY TASKS:
1. Add 1-2 strategic emojis per tweet (not excessive)
2. Make each tweet punchy and stands alone
3. Strengthen the hook to stop scrolls
4. Keep each tweet under 280 characters
5. **REMOVE ALL NUMBERING: 1/6, 1., (1), [1], Tweet 1, etc. DELETE EVERY NUMBER AND PREFIX.**
6. Keep ONLY the raw optimized tweet text

OUTPUT FORMAT - RAW TWEETS SEPARATED BY BLANK LINE ONLY:
[Optimized first tweet with emoji, no numbers, no prefixes]

[Optimized second tweet with emoji, no numbers, no prefixes]

[Optimized third tweet with emoji, no numbers, no prefixes]

[Optimized final tweet with emoji, no numbers, no prefixes]

FAIL CONDITIONS (DO NOT DO THESE):
✗ Output "1/4 First tweet" - WRONG
✗ Output "Tweet 1: ..." - WRONG  
✗ Output "(1) First tweet" - WRONG
✗ Output "[1] First tweet" - WRONG
✓ Output just the tweet text - RIGHT

NOW OPTIMIZE AND OUTPUT ONLY THE TWEETS:"""

    message = HumanMessage(content=prompt)
    response = llm.invoke([message])

    # Parse response: split by double newlines to get individual tweets
    import re
    raw_tweets = response.content.strip().split("\n\n")
    tweets = []
    
    for tweet in raw_tweets:
        tweet = tweet.strip()
        if not tweet:
            continue
            
        # Remove [brackets] wrapper if present
        if tweet.startswith("[") and "]" in tweet:
            bracket_end = tweet.find("]")
            tweet = tweet[bracket_end + 1:].strip()
        
        # Remove all numbering patterns: 1/6, 1., (1), 1), [1], Tweet 1, etc.
        # Match: optional digits, optional slash+digit, optional period/paren/bracket, colon, spaces
        tweet = re.sub(r'^\d+(/\d+)?[.):\-\]]*\s*', '', tweet).strip()
        
        # Remove "Tweet X:", "Tweet X -", "X -" patterns
        tweet = re.sub(r'^(?:Tweet\s+)?\d+\s*[-:)\.]?\s*', '', tweet).strip()
        
        # Remove leading bullets, dashes, asterisks
        tweet = re.sub(r'^[-•*\s]+', '', tweet).strip()
        
        # Final cleanup: remove leading numbers and punctuation
        tweet = re.sub(r'^[\d\s]+[-.):\]]*\s*', '', tweet).strip()
        
        # Only add non-empty tweets with reasonable length (tweets must have substance)
        if tweet and len(tweet) > 15 and not tweet[0].isdigit():
            tweets.append(tweet)

    state["final_thread"] = tweets if tweets else [response.content]
    logger.info(f"[optimizer] finalized thread with {len(tweets)} tweets, removing {len(raw_tweets) - len(tweets)} empty/invalid")
    return state


# Build the StateGraph
def build_viral_thread_graph():
    """Build and compile the LangGraph chain."""
    graph = StateGraph(ThreadState)

    # Add nodes
    graph.add_node("researcher", researcher_agent)
    graph.add_node("writer", writer_agent)
    graph.add_node("optimizer", optimizer_agent)

    # Add edges: researcher → writer → optimizer → end
    graph.add_edge("researcher", "writer")
    graph.add_edge("writer", "optimizer")
    graph.add_edge("optimizer", END)

    # Set entry point
    graph.set_entry_point("researcher")

    return graph.compile()


# Instantiate the compiled graph
viral_thread_graph = build_viral_thread_graph()


def generate_viral_thread(topic: str, user_id: Optional[str] = None) -> List[str]:
    """
    Generate a viral thread for the given topic.
    Optionally uses past user threads as context via pgvector.

    Args:
        topic: The topic/prompt for thread generation
        user_id: Optional Clerk user ID for personalized context

    Returns:
        List of tweet strings forming the thread
    """
    input_state = {
        "topic": topic,
        "research": "",
        "draft": "",
        "final_thread": [],
        "user_id": user_id,
        "similar_threads": [],
    }

    logger.info(f"[generate_viral_thread] generating thread for topic: {topic[:50]}...")
    try:
        result = viral_thread_graph.invoke(input_state)
        final_tweets = result.get("final_thread", [])
        if not final_tweets:
            logger.warning(f"[generate_viral_thread] no tweets returned from graph for topic: {topic[:50]}...")
            return [f"Failed to generate thread for: {topic}"]
        return final_tweets
    except Exception as e:
        logger.error(f"[generate_viral_thread] error generating thread: {e}", exc_info=True)
        return [f"Error generating viral thread: {str(e)}"]
