// lib/presentation/themes/dark_theme.dart
import 'package:flutter/material.dart';
import 'app_theme.dart';

class DarkTheme {
  static ThemeData get theme => ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        
        // Color scheme
        colorScheme: ColorScheme.fromSeed(
          seedColor: AppTheme.primaryBlue,
          brightness: Brightness.dark,
        ).copyWith(
          primary: AppTheme.primaryBlueLight,
          onPrimary: Colors.white,
          secondary: AppTheme.primaryBlue,
          surface: AppTheme.neutral800,
          onSurface: AppTheme.neutral100,
          background: AppTheme.neutral900,
          onBackground: AppTheme.neutral100,
          error: AppTheme.errorRed,
          onError: Colors.white,
        ),

        // Typography
        textTheme: AppTheme.textTheme.apply(
          bodyColor: AppTheme.neutral100,
          displayColor: AppTheme.neutral100,
        ),

        // App bar theme
        appBarTheme: const AppBarTheme(
          backgroundColor: AppTheme.neutral800,
          foregroundColor: AppTheme.neutral100,
          elevation: 0,
          scrolledUnderElevation: 1,
          surfaceTintColor: Colors.transparent,
        ),

        // Card theme
        cardTheme: CardTheme(
          color: AppTheme.neutral800,
          elevation: 2,
          shadowColor: Colors.black26,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),

        // Input decoration theme
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: AppTheme.neutral700,
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 12,
          ),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: const BorderSide(color: AppTheme.neutral600),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: const BorderSide(color: AppTheme.neutral600),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: const BorderSide(color: AppTheme.primaryBlueLight, width: 2),
          ),
          errorBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: const BorderSide(color: AppTheme.errorRed),
          ),
        ),

        // Elevated button theme
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primaryBlueLight,
            foregroundColor: Colors.white,
            elevation: 0,
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8),
            ),
          ),
        ),

        // Outlined button theme
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
            foregroundColor: AppTheme.primaryBlueLight,
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8),
            ),
            side: const BorderSide(color: AppTheme.primaryBlueLight),
          ),
        ),

        // Text button theme
        textButtonTheme: TextButtonThemeData(
          style: TextButton.styleFrom(
            foregroundColor: AppTheme.primaryBlueLight,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          ),
        ),

        // Bottom navigation bar theme
        bottomNavigationBarTheme: const BottomNavigationBarTheme(
          backgroundColor: AppTheme.neutral800,
          selectedItemColor: AppTheme.primaryBlueLight,
          unselectedItemColor: AppTheme.neutral400,
          type: BottomNavigationBarType.fixed,
          elevation: 8,
        ),

        // Floating action button theme
        floatingActionButtonTheme: const FloatingActionButtonThemeData(
          backgroundColor: AppTheme.primaryBlueLight,
          foregroundColor: Colors.white,
        ),

        // Drawer theme
        drawerTheme: const DrawerThemeData(
          backgroundColor: AppTheme.neutral800,
        ),

        // Scaffold background
        scaffoldBackgroundColor: AppTheme.neutral900,
      );
}