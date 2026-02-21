from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import ChatSession, ChatMessage
from .rag import retrieve_context
from .llm import generate_answer


# 🔹 CHAT LIST
@login_required
def chat_list(request):
    chats = ChatSession.objects.filter(user=request.user).order_by("-updated_at")

    if chats.exists():
        return redirect("chat_detail", chat_id=chats.first().id)

    return render(request, "chat/chat_list.html", {"chats": chats})

from django.http import JsonResponse
from django.views.decorators.http import require_POST


@login_required
@require_POST
def rename_chat(request, chat_id):
    chat = get_object_or_404(ChatSession, id=chat_id, user=request.user)

    new_title = request.POST.get("title", "").strip()

    if new_title:
        chat.title = new_title
        chat.save()

    return JsonResponse({"status": "ok", "title": chat.title})

# 🔹 CREATE NEW CHAT
@login_required
def create_chat(request):
    chat = ChatSession.objects.create(
        user=request.user,
        title="New Conversation"
    )
    return redirect("chat_detail", chat_id=chat.id)

from django.views.decorators.http import require_POST


@login_required
@require_POST
def delete_chat(request, chat_id):
    chat = get_object_or_404(ChatSession, id=chat_id, user=request.user)
    chat.delete()
    return redirect("chat_list")

# 🔹 CHAT DETAIL (Main Interaction View)
@login_required
def chat_detail(request, chat_id):
    chat = get_object_or_404(ChatSession, id=chat_id, user=request.user)

    chats = ChatSession.objects.filter(user=request.user).order_by("-updated_at")
    messages = chat.messages.order_by("created_at")

    if request.method == "POST":
        user_input = request.POST.get("message", "").strip()
        if user_input:
            # 1️⃣ Save User Message
            ChatMessage.objects.create(
                chat=chat,
                role="user",
                content=user_input
            )

            # 2️⃣ Update Chat Title (only if first message)
            if messages.count() == 0:
                new_title = user_input[:35] + ("..." if len(user_input) > 35 else "")
                chat.title = new_title
                chat.save()

            try:
                # 3️⃣ Retrieve Context
                context = retrieve_context(user_input)
                print("🔎 DEBUG - User Input:", user_input)
                print("🔎 DEBUG - Retrieved Context:", context[:100] if context else "None")

                if not context:
                    ai_response = "Please ask a legal question related to Indian law or IPC."
                else:
                    # 4️⃣ Build Optimized Prompt
                    prompt = f"""
Answer using ONLY the retrieved legal text below.

Retrieved Text:
{context[:1500]}

Question:
{user_input}

Give a concise structured legal answer.
"""

                    # 5️⃣ Generate AI Response
                    ai_response = generate_answer(prompt)

            except Exception as e:
                ai_response = f"⚠ System Error: {str(e)}"

            # 6️⃣ Save Assistant Response
            ChatMessage.objects.create(
                chat=chat,
                role="assistant",
                content=ai_response
            )

        return redirect("chat_detail", chat_id=chat.id)

    return render(request, "chat/chat_detail.html", {
        "chat": chat,
        "messages": messages,
        "chats": chats,
        "active_chat": chat
    })