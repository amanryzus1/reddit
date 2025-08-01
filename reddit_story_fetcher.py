import praw
import yaml
import json
from datetime import datetime

# --- Your Reddit App Credentials (Replace USERNAME below) ---
CLIENT_ID = "IiQsPLXbq1koYijL7dtX8w"
CLIENT_SECRET = "N8XTR2n4tGHQAUUeyMsqtQO_4KyguQ"
USER_AGENT = "script:full_story_video:v1.0 (by u/yourusername)"  # <-- REPLACE 'yourusername'

# --- Configuration ---
VIRAL_TAGS = [
    "aita", "askreddit", "redditstories", "redditposts", "redditstory",
    "relationship", "relationships", "relationshipadvice", "cheating",
    "breakup", "revenge", "toxic relationship", "crazy ex", "psycho ex",
    "confession", "amitheasshole", "update", "bestof", "TIFU", "funny",
    "memes", "meme", "drama", "karma", "emotional", "infidelity",
    "betrayal", "dramatic", "insane", "wild", "unbelievable"
]

SUBREDDITS = [
    "relationships",
    "relationship_advice",
    "AmItheAsshole",
    "BestofRedditorUpdates",
    "TIFU",
    "AskReddit"
]


# --- Helper: Filter out questions ---
def is_story_post(title):
    question_words = (
        "what", "do you", "does", "did", "how", "why", "have you", "has anyone",
        "can you", "is", "are", "who", "when", "where", "will", "should", "could"
    )
    title_lower = title.strip().lower()
    if title_lower.endswith('?'):
        return False
    if any(title_lower.startswith(qw) for qw in question_words):
        return False
    return True


# --- Class for fetching and saving stories ---
class RedditStoryFetcher:
    def __init__(self):
        try:
            self.reddit = praw.Reddit(
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                user_agent=USER_AGENT
            )
            print("✅ Connected to Reddit API")
        except Exception as e:
            print(f"❌ Connection error: {e}")
            raise

    def fetch_stories_by_tags(self, subreddits=None, tags=None, sort="top",
                              timeframe="week", limit_per_sub=10, min_score=50, include_comments=False):
        if subreddits is None:
            subreddits = SUBREDDITS
        if tags is None:
            tags = VIRAL_TAGS
        stories = []
        tags_lower = [tag.lower() for tag in tags]
        for sub in subreddits:
            try:
                print(f"🔎 Fetching r/{sub}...")
                subreddit_obj = self.reddit.subreddit(sub)

                if sort == "top":
                    submissions = subreddit_obj.top(time_filter=timeframe, limit=limit_per_sub * 2)
                elif sort == "hot":
                    submissions = subreddit_obj.hot(limit=limit_per_sub * 2)
                elif sort == "new":
                    submissions = subreddit_obj.new(limit=limit_per_sub * 2)
                else:
                    submissions = subreddit_obj.top(time_filter=timeframe, limit=limit_per_sub * 2)

                count = 0
                for submission in submissions:
                    if count >= limit_per_sub:
                        break
                    title = submission.title
                    title_lower = title.lower()

                    if (any(tag in title_lower for tag in tags_lower) and
                            is_story_post(title) and
                            getattr(submission, 'score', 0) >= min_score and
                            hasattr(submission, 'selftext')):

                        story_text = submission.selftext.strip()
                        if not story_text:
                            continue
                        story_data = {
                            "title": title,
                            "full_story": story_text,
                            "story_length": len(story_text),
                            "author": str(submission.author) if submission.author else "[deleted]",
                            "score": submission.score,
                            "num_comments": submission.num_comments,
                            "url": submission.url,
                            "permalink": submission.permalink,
                            "subreddit": sub,
                            "created_utc": submission.created_utc,
                            "created_date": datetime.fromtimestamp(submission.created_utc).strftime(
                                "%Y-%m-%d %H:%M:%S"),
                            "has_comments": getattr(submission, 'comments', None) is not None
                        }
                        # Optionally include top comments
                        if include_comments:
                            try:
                                submission.comments.replace_more(limit=0)
                                top_comments = []
                                for comment in submission.comments[:3]:
                                    top_comments.append({
                                        "author": str(comment.author) if comment.author else "[deleted]",
                                        "score": comment.score,
                                        "body": comment.body
                                    })
                                story_data["top_comments"] = top_comments
                            except Exception:
                                story_data["top_comments"] = []

                        stories.append(story_data)
                        count += 1
                        print(f"  ✓ {title[:60]}... ({len(story_text)} chars)")
            except Exception as e:
                print(f"❌ Error fetching r/{sub}: {e}")
        stories.sort(key=lambda x: x['score'], reverse=True)
        print(f"🚀 Total stories fetched: {len(stories)}")
        return stories

    def get_relationship_stories(self, limit_per_sub=5, min_score=100):
        return self.fetch_stories_by_tags(
            subreddits=["relationships", "relationship_advice", "AmItheAsshole"],
            tags=["crazy ex", "toxic", "cheating", "breakup", "revenge", "betrayal", "drama"],
            sort="top",
            timeframe="week",
            limit_per_sub=limit_per_sub,
            min_score=min_score,
            include_comments=True
        )

    def save_stories_to_yaml(self, stories, filename="viral_stories_full.yaml"):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                yaml.dump(stories, f, allow_unicode=True, sort_keys=False, default_flow_style=False, indent=2)
            print(f"✅ Stories saved as YAML: {filename}")
        except Exception as e:
            print(f"❌ YAML save error: {e}")

    def save_stories_to_json(self, stories, filename="viral_stories_full.json"):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(stories, f, ensure_ascii=False, indent=2)
            print(f"✅ Stories saved as JSON: {filename}")
        except Exception as e:
            print(f"❌ JSON save error: {e}")

    def display_preview(self, stories, max=3):
        print(f"\n🔎 Preview Top {min(max, len(stories))} Stories:")
        for i, s in enumerate(stories[:max], 1):
            print(f"\n{i}. {s['title']}")
            print(f"   Subreddit: r/{s['subreddit']}")
            print(f"   Author: {s['author']} | Score: {s['score']} | Comments: {s['num_comments']}")
            print(f"   Date: {s['created_date']}")
            preview = s['full_story'][:300] + ("..." if len(s['full_story']) > 300 else "")
            print(f"   Story preview:\n{preview}\n")
            print("-" * 60)


# --- Main execution ---
def main():
    print("🔥 Reddit Viral Story Fetcher - Full Content Version\n")
    fetcher = RedditStoryFetcher()

    print("🔎 Fetching stories...")
    stories = fetcher.get_relationship_stories(limit_per_sub=5, min_score=100)

    if stories:
        fetcher.display_preview(stories)
        fetcher.save_stories_to_yaml(stories)
        # fetcher.save_stories_to_json(stories)
        print("\n🎉 Stories saved in 'viral_stories_full.yaml' and 'viral_stories_full.json'.")
    else:
        print("⚠️ No stories found. Try relaxing filters.")


if __name__ == "__main__":
    main()
