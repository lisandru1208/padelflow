// app/club/create.tsx
// Écran de création d'un club

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Alert,
  TouchableOpacity,
} from 'react-native';
import { router, Stack } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../context/AuthContext';
import { createClub } from '../../services/api';
import { Button, Input } from '../../components';
import { Colors, Spacing, FontSizes, BorderRadius } from '../../constants/theme';

export default function CreateClubScreen() {
  const { token } = useAuth();
  const [name, setName] = useState('');
  const [city, setCity] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<{ name?: string }>({});

  const validate = (): boolean => {
    const newErrors: { name?: string } = {};

    if (!name.trim()) {
      newErrors.name = 'Le nom du club est requis';
    } else if (name.trim().length < 2) {
      newErrors.name = 'Le nom doit contenir au moins 2 caractères';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleCreate = async () => {
    if (!validate() || !token) return;

    setIsLoading(true);
    try {
      await createClub(token, name.trim(), city.trim() || undefined);
      Alert.alert('Succès', 'Club créé avec succès !', [
        { text: 'OK', onPress: () => router.back() },
      ]);
    } catch (e: any) {
      Alert.alert('Erreur', e.message || 'Impossible de créer le club');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <Stack.Screen
        options={{
          title: 'Nouveau Club',
          headerShown: true,
          headerStyle: { backgroundColor: Colors.surface },
          headerTintColor: Colors.text,
          headerLeft: () => (
            <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
              <Ionicons name="arrow-back" size={24} color={Colors.text} />
            </TouchableOpacity>
          ),
        }}
      />
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.container}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
        >
          <View style={styles.iconContainer}>
            <Ionicons name="business" size={48} color={Colors.primary} />
          </View>
          <Text style={styles.title}>Créer un Club</Text>
          <Text style={styles.subtitle}>
            Renseignez les informations de votre club de padel
          </Text>

          <View style={styles.form}>
            <Input
              label="Nom du club *"
              placeholder="Ex: Club Padel Paris"
              value={name}
              onChangeText={setName}
              leftIcon="business-outline"
              error={errors.name}
              autoFocus
            />

            <Input
              label="Ville (optionnel)"
              placeholder="Ex: Paris"
              value={city}
              onChangeText={setCity}
              leftIcon="location-outline"
            />

            <View style={styles.buttonsContainer}>
              <Button
                title="Annuler"
                onPress={() => router.back()}
                variant="outline"
                style={styles.button}
              />
              <Button
                title="Créer"
                onPress={handleCreate}
                loading={isLoading}
                style={styles.button}
              />
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  backButton: {
    padding: Spacing.sm,
    marginLeft: Spacing.xs,
  },
  scrollContent: {
    padding: Spacing.lg,
  },
  iconContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: Colors.infoLight,
    alignItems: 'center',
    justifyContent: 'center',
    alignSelf: 'center',
    marginBottom: Spacing.md,
    marginTop: Spacing.lg,
  },
  title: {
    fontSize: FontSizes.xxl,
    fontWeight: 'bold',
    color: Colors.text,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: FontSizes.md,
    color: Colors.textSecondary,
    textAlign: 'center',
    marginTop: Spacing.xs,
    marginBottom: Spacing.xl,
  },
  form: {
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.lg,
    padding: Spacing.lg,
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  buttonsContainer: {
    flexDirection: 'row',
    gap: Spacing.md,
    marginTop: Spacing.md,
  },
  button: {
    flex: 1,
  },
});