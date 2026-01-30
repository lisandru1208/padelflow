// app/tournament/create.tsx
// Écran de création d'un tournoi

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
  Switch,
  Modal,
} from 'react-native';
import { router, Stack, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import DateTimePicker, { DateTimePickerEvent } from '@react-native-community/datetimepicker';
import { useAuth } from '../../context/AuthContext';
import { createTournament } from '../../services/api';
import { Button, Input, Card } from '../../components';
import { Colors, Spacing, FontSizes, BorderRadius } from '../../constants/theme';

// Options pour les catégories
const CATEGORIES = ['P25', 'P100', 'P250', 'P500', 'P1000', 'P2000'];

// Options pour le genre
const GENDERS = [
  { value: 'male', label: 'Hommes' },
  { value: 'female', label: 'Femmes' },
  { value: 'mixed', label: 'Mixte' },
];

export default function CreateTournamentScreen() {
  const { clubId } = useLocalSearchParams<{ clubId: string }>();
  const { token } = useAuth();

  const [name, setName] = useState('');
  const [category, setCategory] = useState('P250');
  const [gender, setGender] = useState('male');
  const [startDate, setStartDate] = useState<Date | null>(null);
  const [endDate, setEndDate] = useState<Date | null>(null);
  const [indoor, setIndoor] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<{ name?: string; startDate?: string }>({});

  // États pour les date pickers
  const [showStartPicker, setShowStartPicker] = useState(false);
  const [showEndPicker, setShowEndPicker] = useState(false);

  const formatDateDisplay = (date: Date | null): string => {
    if (!date) return '';
    return date.toLocaleDateString('fr-FR', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  };

  const formatDateAPI = (date: Date): string => {
    return date.toISOString().split('T')[0];
  };

  const handleStartDateChange = (event: DateTimePickerEvent, selectedDate?: Date) => {
    if (Platform.OS === 'android') {
      setShowStartPicker(false);
    }
    if (event.type === 'set' && selectedDate) {
      setStartDate(selectedDate);
      setErrors((prev) => ({ ...prev, startDate: undefined }));
    }
  };

  const handleEndDateChange = (event: DateTimePickerEvent, selectedDate?: Date) => {
    if (Platform.OS === 'android') {
      setShowEndPicker(false);
    }
    if (event.type === 'set' && selectedDate) {
      setEndDate(selectedDate);
    }
  };

  const validate = (): boolean => {
    const newErrors: { name?: string; startDate?: string } = {};

    if (!name.trim()) {
      newErrors.name = 'Le nom du tournoi est requis';
    }

    if (!startDate) {
      newErrors.startDate = 'La date de début est requise';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleCreate = async () => {
    if (!validate() || !token || !clubId || !startDate) return;

    setIsLoading(true);
    try {
      await createTournament(token, clubId, {
        name: name.trim(),
        category,
        gender,
        start_date: formatDateAPI(startDate),
        end_date: endDate ? formatDateAPI(endDate) : undefined,
        indoor,
      });
      Alert.alert('Succès', 'Tournoi créé avec succès !', [
        { text: 'OK', onPress: () => router.back() },
      ]);
    } catch (e: any) {
      Alert.alert('Erreur', e.message || 'Impossible de créer le tournoi');
    } finally {
      setIsLoading(false);
    }
  };

  const renderDatePickerIOS = (
    show: boolean,
    setShow: (value: boolean) => void,
    date: Date | null,
    onChange: (event: DateTimePickerEvent, date?: Date) => void,
    minimumDate?: Date
  ) => {
    if (!show || Platform.OS !== 'ios') return null;

    return (
      <Modal transparent animationType="slide" visible={show}>
        <View style={styles.datePickerModal}>
          <View style={styles.datePickerContent}>
            <View style={styles.datePickerHeader}>
              <TouchableOpacity onPress={() => setShow(false)}>
                <Text style={styles.datePickerCancel}>Annuler</Text>
              </TouchableOpacity>
              <TouchableOpacity onPress={() => setShow(false)}>
                <Text style={styles.datePickerDone}>OK</Text>
              </TouchableOpacity>
            </View>
            <DateTimePicker
              value={date || new Date()}
              mode="date"
              display="spinner"
              onChange={onChange}
              minimumDate={minimumDate}
              locale="fr-FR"
            />
          </View>
        </View>
      </Modal>
    );
  };

  return (
    <>
      <Stack.Screen
        options={{
          title: 'Nouveau Tournoi',
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
            <Ionicons name="trophy" size={48} color={Colors.accent} />
          </View>
          <Text style={styles.title}>Créer un Tournoi</Text>
          <Text style={styles.subtitle}>
            Renseignez les informations de votre compétition
          </Text>

          <Card variant="elevated" style={styles.formCard}>
            {/* Nom du tournoi */}
            <Input
              label="Nom du tournoi *"
              placeholder="Ex: Open de Printemps 2025"
              value={name}
              onChangeText={setName}
              leftIcon="trophy-outline"
              error={errors.name}
            />

            {/* Catégorie */}
            <Text style={styles.label}>Catégorie *</Text>
            <View style={styles.optionsRow}>
              {CATEGORIES.map((cat) => (
                <TouchableOpacity
                  key={cat}
                  style={[
                    styles.optionButton,
                    category === cat && styles.optionButtonActive,
                  ]}
                  onPress={() => setCategory(cat)}
                >
                  <Text
                    style={[
                      styles.optionText,
                      category === cat && styles.optionTextActive,
                    ]}
                  >
                    {cat}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* Genre */}
            <Text style={styles.label}>Genre *</Text>
            <View style={styles.optionsRow}>
              {GENDERS.map((g) => (
                <TouchableOpacity
                  key={g.value}
                  style={[
                    styles.optionButton,
                    styles.genderButton,
                    gender === g.value && styles.optionButtonActive,
                  ]}
                  onPress={() => setGender(g.value)}
                >
                  <Text
                    style={[
                      styles.optionText,
                      gender === g.value && styles.optionTextActive,
                    ]}
                  >
                    {g.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* Date de début */}
            <Text style={styles.label}>Date de début *</Text>
            <TouchableOpacity
              style={[
                styles.dateButton,
                errors.startDate && styles.dateButtonError,
              ]}
              onPress={() => setShowStartPicker(true)}
            >
              <Ionicons name="calendar-outline" size={20} color={Colors.primary} />
              <Text
                style={[
                  styles.dateButtonText,
                  !startDate && styles.dateButtonPlaceholder,
                ]}
              >
                {startDate ? formatDateDisplay(startDate) : 'Sélectionner une date'}
              </Text>
            </TouchableOpacity>
            {errors.startDate && (
              <Text style={styles.errorText}>{errors.startDate}</Text>
            )}

            {/* Date de fin */}
            <Text style={styles.label}>Date de fin (optionnel)</Text>
            <TouchableOpacity
              style={styles.dateButton}
              onPress={() => setShowEndPicker(true)}
            >
              <Ionicons name="calendar-outline" size={20} color={Colors.primary} />
              <Text
                style={[
                  styles.dateButtonText,
                  !endDate && styles.dateButtonPlaceholder,
                ]}
              >
                {endDate ? formatDateDisplay(endDate) : 'Sélectionner une date'}
              </Text>
              {endDate && (
                <TouchableOpacity
                  onPress={() => setEndDate(null)}
                  style={styles.clearDateButton}
                >
                  <Ionicons name="close-circle" size={20} color={Colors.textLight} />
                </TouchableOpacity>
              )}
            </TouchableOpacity>

            {/* Indoor */}
            <View style={styles.switchRow}>
              <View style={styles.switchInfo}>
                <Ionicons
                  name={indoor ? 'home' : 'sunny'}
                  size={20}
                  color={Colors.primary}
                />
                <Text style={styles.switchLabel}>Tournoi en salle (indoor)</Text>
              </View>
              <Switch
                value={indoor}
                onValueChange={setIndoor}
                trackColor={{ false: Colors.border, true: Colors.primaryLight }}
                thumbColor={indoor ? Colors.primary : Colors.surface}
              />
            </View>

            {/* Boutons */}
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
          </Card>
        </ScrollView>
      </KeyboardAvoidingView>

      {/* Date Pickers Android */}
      {Platform.OS === 'android' && showStartPicker && (
        <DateTimePicker
          value={startDate || new Date()}
          mode="date"
          display="default"
          onChange={handleStartDateChange}
          minimumDate={new Date()}
        />
      )}

      {Platform.OS === 'android' && showEndPicker && (
        <DateTimePicker
          value={endDate || startDate || new Date()}
          mode="date"
          display="default"
          onChange={handleEndDateChange}
          minimumDate={startDate || new Date()}
        />
      )}

      {/* Date Pickers iOS */}
      {renderDatePickerIOS(
        showStartPicker,
        setShowStartPicker,
        startDate,
        handleStartDateChange,
        new Date()
      )}

      {renderDatePickerIOS(
        showEndPicker,
        setShowEndPicker,
        endDate,
        handleEndDateChange,
        startDate || new Date()
      )}
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
    backgroundColor: Colors.warningLight,
    alignItems: 'center',
    justifyContent: 'center',
    alignSelf: 'center',
    marginBottom: Spacing.md,
    marginTop: Spacing.md,
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
  formCard: {
    padding: Spacing.lg,
  },
  label: {
    fontSize: FontSizes.sm,
    fontWeight: '600',
    color: Colors.text,
    marginBottom: Spacing.sm,
    marginTop: Spacing.sm,
  },
  optionsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.sm,
    marginBottom: Spacing.md,
  },
  optionButton: {
    paddingVertical: Spacing.sm,
    paddingHorizontal: Spacing.md,
    borderRadius: BorderRadius.md,
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: Colors.surface,
  },
  genderButton: {
    flex: 1,
    alignItems: 'center',
  },
  optionButtonActive: {
    borderColor: Colors.primary,
    backgroundColor: Colors.infoLight,
  },
  optionText: {
    fontSize: FontSizes.sm,
    color: Colors.textSecondary,
    fontWeight: '500',
  },
  optionTextActive: {
    color: Colors.primary,
    fontWeight: '600',
  },
  dateButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.surface,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: BorderRadius.md,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.md,
    marginBottom: Spacing.md,
  },
  dateButtonError: {
    borderColor: Colors.error,
  },
  dateButtonText: {
    flex: 1,
    fontSize: FontSizes.md,
    color: Colors.text,
    marginLeft: Spacing.sm,
  },
  dateButtonPlaceholder: {
    color: Colors.textLight,
  },
  clearDateButton: {
    padding: Spacing.xs,
  },
  errorText: {
    fontSize: FontSizes.xs,
    color: Colors.error,
    marginTop: -Spacing.sm,
    marginBottom: Spacing.md,
    marginLeft: Spacing.xs,
  },
  switchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: Spacing.md,
    marginBottom: Spacing.md,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
  },
  switchInfo: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  switchLabel: {
    fontSize: FontSizes.md,
    color: Colors.text,
    marginLeft: Spacing.sm,
  },
  buttonsContainer: {
    flexDirection: 'row',
    gap: Spacing.md,
    marginTop: Spacing.sm,
  },
  button: {
    flex: 1,
  },
  // Date picker modal iOS
  datePickerModal: {
    flex: 1,
    justifyContent: 'flex-end',
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
  },
  datePickerContent: {
    backgroundColor: Colors.surface,
    borderTopLeftRadius: BorderRadius.xl,
    borderTopRightRadius: BorderRadius.xl,
    paddingBottom: Spacing.xl,
  },
  datePickerHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: Spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  datePickerCancel: {
    fontSize: FontSizes.md,
    color: Colors.textSecondary,
  },
  datePickerDone: {
    fontSize: FontSizes.md,
    color: Colors.primary,
    fontWeight: '600',
  },
});