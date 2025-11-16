"""
Complete indexing script for scraped pages and insights
Handles chunking, deduplication, error handling, and rate limiting
"""

from app.core.mongo import connect_to_mongo
from app.core.vector_store import chroma_client
from openai import OpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from tqdm import tqdm
import os
import time

# Connect to MongoDB
mongo = connect_to_mongo()
scraped_pages_collection = mongo.scraped_pages
insights_collection = mongo.insights

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
embedding_model = "text-embedding-3-small"

# Get or create ChromaDB collection
chroma_collection = chroma_client.get_or_create_collection(
    name="hda_documents",
    metadata={"description": "H_DA scraped pages and insights with embeddings"}
)

# Text splitter for long documents
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
)


def embed_text(text: str) -> list:
    """Generate embedding using OpenAI"""
    try:
        response = client.embeddings.create(
            input=text,
            model=embedding_model
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"❌ Error generating embedding: {e}")
        return None


def is_already_indexed(doc_id: str) -> bool:
    """Check if document is already in ChromaDB"""
    try:
        result = chroma_collection.get(ids=[doc_id])
        return len(result['ids']) > 0
    except:
        return False


def index_scraped_pages():
    """Index all scraped pages from MongoDB into ChromaDB"""
    print("\n" + "=" * 60)
    print("📄 INDEXING SCRAPED PAGES")
    print("=" * 60)

    all_docs = list(scraped_pages_collection.find({}))
    print(f"Found {len(all_docs)} scraped pages to process\n")

    indexed_count = 0
    skipped_count = 0
    error_count = 0
    total_chunks = 0

    for doc in tqdm(all_docs, desc="Processing pages"):
        try:
            doc_id = str(doc["_id"])
            title = doc.get("title", "Untitled")
            url = doc.get("url", "")
            content = doc.get("content", "")
            headings = doc.get("headings", [])
            paragraphs = doc.get("paragraphs", [])
            tags = doc.get("tags", [])

            # Combine all text content
            full_text = content

            if headings and isinstance(headings, list):
                full_text += "\n\n" + "\n".join([str(h) for h in headings])

            if paragraphs and isinstance(paragraphs, list):
                full_text += "\n\n" + "\n".join([str(p) for p in paragraphs])

            # Skip if content too short
            if len(full_text.strip()) < 50:
                print(f"\n⏭️  Skipping (too short): {title}")
                skipped_count += 1
                continue

            # Split into chunks
            chunks = text_splitter.split_text(full_text)

            for i, chunk in enumerate(chunks):
                chunk_id = f"page_{doc_id}_chunk_{i}"

                # Check if already indexed
                if is_already_indexed(chunk_id):
                    continue

                # Generate embedding
                vector = embed_text(chunk)

                if vector:
                    # Prepare metadata
                    metadata = {
                        "type": "page",
                        "title": title,
                        "url": url,
                        "chunk_index": i,
                        "total_chunks": len(chunks)
                    }

                    # Add tags if present
                    if tags and isinstance(tags, list):
                        metadata["tags"] = ",".join([str(t) for t in tags])

                    # Add to ChromaDB
                    chroma_collection.add(
                        ids=[chunk_id],
                        embeddings=[vector],
                        documents=[chunk],
                        metadatas=[metadata]
                    )

                    indexed_count += 1
                    total_chunks += 1

                    # Rate limiting (3000 RPM = 50 RPS, so 0.02s delay is safe)
                    time.sleep(0.02)
                else:
                    error_count += 1

        except Exception as e:
            print(f"\n❌ Error processing document {doc.get('_id')}: {e}")
            error_count += 1
            continue

    print(f"\n📊 Scraped Pages Summary:")
    print(f"   ✅ Indexed: {indexed_count} chunks from {len(all_docs)} pages")
    print(f"   ⏭️  Skipped: {skipped_count}")
    print(f"   ❌ Errors: {error_count}")
    print(f"   📦 Total chunks created: {total_chunks}")


def index_insights():
    """Index all insights from MongoDB into ChromaDB"""
    print("\n" + "=" * 60)
    print("💡 INDEXING INSIGHTS")
    print("=" * 60)

    all_insights = list(insights_collection.find({}))
    print(f"Found {len(all_insights)} insights to process\n")

    indexed_count = 0
    skipped_count = 0
    error_count = 0

    for insight in tqdm(all_insights, desc="Processing insights"):
        try:
            insight_id = f"insight_{str(insight['_id'])}"
            topic = insight.get("topic", "Unknown")
            content = insight.get("content", "")
            source = insight.get("source", "")
            tags = insight.get("tags", [])

            # Skip if content too short
            if len(content.strip()) < 20:
                print(f"\n⏭️  Skipping (too short): {topic}")
                skipped_count += 1
                continue

            # Check if already indexed
            if is_already_indexed(insight_id):
                continue

            # Generate embedding
            vector = embed_text(content)

            if vector:
                # Prepare metadata
                metadata = {
                    "type": "insight",
                    "topic": topic,
                    "source": source or "insight"
                }

                # Add tags if present
                if tags and isinstance(tags, list):
                    metadata["tags"] = ",".join([str(t) for t in tags])

                # Add to ChromaDB
                chroma_collection.add(
                    ids=[insight_id],
                    embeddings=[vector],
                    documents=[content],
                    metadatas=[metadata]
                )

                indexed_count += 1

                # Rate limiting
                time.sleep(0.02)
            else:
                error_count += 1

        except Exception as e:
            print(f"\n❌ Error processing insight {insight.get('_id')}: {e}")
            error_count += 1
            continue

    print(f"\n📊 Insights Summary:")
    print(f"   ✅ Indexed: {indexed_count}")
    print(f"   ⏭️  Skipped: {skipped_count}")
    print(f"   ❌ Errors: {error_count}")


def show_collection_stats():
    """Display ChromaDB collection statistics"""
    print("\n" + "=" * 60)
    print("📊 CHROMADB COLLECTION STATISTICS")
    print("=" * 60)

    try:
        total_count = chroma_collection.count()
        print(f"\n✅ Total documents in collection: {total_count}")

        # Get sample documents
        sample = chroma_collection.peek(limit=5)

        print(f"\n📋 Sample Documents:")
        for i, (doc_id, metadata, document) in enumerate(zip(
                sample['ids'],
                sample['metadatas'],
                sample['documents']
        )):
            print(f"\n{i + 1}. ID: {doc_id}")
            print(f"   Type: {metadata.get('type')}")
            if metadata.get('type') == 'page':
                print(f"   Title: {metadata.get('title')}")
                print(f"   URL: {metadata.get('url')}")
                print(f"   Chunk: {metadata.get('chunk_index', 0) + 1}/{metadata.get('total_chunks', 1)}")
            else:
                print(f"   Topic: {metadata.get('topic')}")
                print(f"   Source: {metadata.get('source')}")
            print(f"   Content preview: {document[:100]}...")

        # Count by type
        pages_count = len([m for m in sample['metadatas'] if m.get('type') == 'page'])
        insights_count = len([m for m in sample['metadatas'] if m.get('type') == 'insight'])

        print(f"\n📈 Breakdown (from sample):")
        print(f"   📄 Pages: {pages_count}")
        print(f"   💡 Insights: {insights_count}")

    except Exception as e:
        print(f"❌ Error getting collection stats: {e}")


def main():
    """Main execution function"""
    print("\n" + "=" * 60)
    print("🚀 STARTING VECTOR INDEXING PROCESS")
    print("=" * 60)
    print(f"\nEmbedding Model: {embedding_model}")
    print(f"Collection Name: hda_documents")

    try:
        # Index scraped pages
        index_scraped_pages()

        # Index insights
        index_insights()

        # Show statistics
        show_collection_stats()

        print("\n" + "=" * 60)
        print("✅ INDEXING COMPLETED SUCCESSFULLY!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Fatal error during indexing: {e}")
        raise


if __name__ == "__main__":
    main()