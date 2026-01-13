import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'screens/login_screen.dart';

void main() {
  runApp(const MedDataApp());
}

class MedDataApp extends StatelessWidget {
  const MedDataApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'MedScript Pro',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        // "Adaptive Deep" Theme defined in the blueprint
        scaffoldBackgroundColor: const Color(0xFF0F172A), // Midnight Blue
        primaryColor: const Color(0xFF00F260), // Electric Green
        brightness: Brightness.dark,
        textTheme: GoogleFonts.jetbrainsMonoTextTheme(
          Theme.of(context).textTheme.apply(bodyColor: Colors.white),
        ),
        useMaterial3: true,
      ),
      // We will create the LoginScreen next
      home: const LoginScreen(),
    );
  }
}