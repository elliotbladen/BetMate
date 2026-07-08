import React, { useEffect, useRef, useState } from 'react';
import {
  View, Text, StyleSheet, TextInput, FlatList, Pressable,
  SafeAreaView, KeyboardAvoidingView, Platform, ActivityIndicator,
} from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { C } from '../../constants/colors';
import { sendBazMessage, BASE_URL } from '../../lib/api';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  streaming?: boolean;
}

export default function BazScreen() {
  const { home, away } = useLocalSearchParams<{ home?: string; away?: string }>();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [brainOnline, setBrainOnline] = useState<boolean | null>(null);
  const listRef = useRef<FlatList<Message>>(null);

  useEffect(() => {
    fetch(`${BASE_URL}/api/chat`, { method: 'HEAD' })
      .then(() => setBrainOnline(true))
      .catch(() => setBrainOnline(false));

    const greeting = home && away
      ? `Ready to break down ${home} vs ${away}. What do you want to know?`
      : "G'day, I'm Baz — your BetMate AI. Ask me about any game, market, or price move.";

    setMessages([{ id: 'greeting', role: 'assistant', content: greeting }]);
  }, [home, away]);

  async function send() {
    const text = input.trim();
    if (!text || sending) return;

    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: text };
    const assistantId = `a-${Date.now()}`;
    const assistantMsg: Message = { id: assistantId, role: 'assistant', content: '', streaming: true };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInput('');
    setSending(true);

    const history = [...messages, userMsg].map((m) => ({ role: m.role, content: m.content }));

    try {
      await sendBazMessage(history, (chunk) => {
        setMessages((prev) =>
          prev.map((m) => m.id === assistantId ? { ...m, content: m.content + chunk } : m)
        );
        listRef.current?.scrollToEnd({ animated: true });
      });
      setMessages((prev) =>
        prev.map((m) => m.id === assistantId ? { ...m, streaming: false } : m)
      );
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: 'Sorry, something went wrong. Try again.', streaming: false }
            : m
        )
      );
    } finally {
      setSending(false);
    }
  }

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={90}
      >
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.title}>Baz</Text>
            <Text style={styles.subtitle}>
              {home && away ? `${home} vs ${away}` : 'BetMate AI'}
            </Text>
          </View>
          {brainOnline !== null && (
            <View style={styles.statusRow}>
              <View style={[styles.statusDot, { backgroundColor: brainOnline ? C.accent : C.amber }]} />
              <Text style={styles.statusText}>{brainOnline ? 'Brain online' : 'Brain offline'}</Text>
            </View>
          )}
        </View>

        {/* Messages */}
        <FlatList
          ref={listRef}
          data={messages}
          keyExtractor={(m) => m.id}
          contentContainerStyle={styles.msgList}
          showsVerticalScrollIndicator={false}
          onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: true })}
          renderItem={({ item }) => (
            <View style={[styles.bubble, item.role === 'user' ? styles.bubbleUser : styles.bubbleBaz]}>
              {item.role === 'assistant' && (
                <Text style={styles.bazLabel}>BAZ</Text>
              )}
              <Text style={[styles.bubbleText, item.role === 'user' && styles.bubbleTextUser]}>
                {item.content || (item.streaming ? '' : '')}
              </Text>
              {item.streaming && item.content === '' && (
                <ActivityIndicator size="small" color={C.accent} style={{ marginTop: 4 }} />
              )}
              {item.streaming && item.content.length > 0 && (
                <Text style={styles.cursor}>▊</Text>
              )}
            </View>
          )}
        />

        {/* Input */}
        <View style={styles.inputRow}>
          <TextInput
            style={styles.input}
            value={input}
            onChangeText={setInput}
            placeholder="Ask Baz anything..."
            placeholderTextColor={C.textMuted}
            multiline
            maxLength={500}
            returnKeyType="send"
            onSubmitEditing={send}
            blurOnSubmit
          />
          <Pressable
            onPress={send}
            disabled={!input.trim() || sending}
            style={[styles.sendBtn, (!input.trim() || sending) && styles.sendBtnDisabled]}
          >
            <Text style={styles.sendText}>↑</Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: C.bg,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: C.cardBorder,
  },
  title: {
    color: C.white,
    fontSize: 18,
    fontWeight: '900',
    letterSpacing: -0.3,
  },
  subtitle: {
    color: C.textMuted,
    fontSize: 10,
    fontWeight: '600',
    letterSpacing: 0.8,
    textTransform: 'uppercase',
    marginTop: 2,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  statusDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
  },
  statusText: {
    color: C.textMuted,
    fontSize: 10,
    fontWeight: '600',
    letterSpacing: 0.5,
  },
  msgList: {
    padding: 14,
    gap: 10,
    paddingBottom: 20,
  },
  bubble: {
    maxWidth: '85%',
    borderRadius: 14,
    padding: 12,
  },
  bubbleUser: {
    backgroundColor: C.accent,
    alignSelf: 'flex-end',
    borderBottomRightRadius: 4,
  },
  bubbleBaz: {
    backgroundColor: C.card,
    alignSelf: 'flex-start',
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderColor: C.cardBorder,
  },
  bazLabel: {
    color: C.accent,
    fontSize: 8,
    fontWeight: '900',
    letterSpacing: 1.5,
    marginBottom: 4,
  },
  bubbleText: {
    color: C.textPrimary,
    fontSize: 14,
    lineHeight: 20,
  },
  bubbleTextUser: {
    color: '#000',
    fontWeight: '600',
  },
  cursor: {
    color: C.accent,
    fontSize: 14,
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    padding: 12,
    gap: 8,
    borderTopWidth: 1,
    borderTopColor: C.cardBorder,
    backgroundColor: C.bg,
  },
  input: {
    flex: 1,
    backgroundColor: C.card,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: C.cardBorder,
    color: C.textPrimary,
    fontSize: 14,
    paddingHorizontal: 14,
    paddingTop: 10,
    paddingBottom: 10,
    maxHeight: 100,
  },
  sendBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: C.accent,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendBtnDisabled: {
    opacity: 0.35,
  },
  sendText: {
    color: '#000',
    fontSize: 18,
    fontWeight: '900',
  },
});
