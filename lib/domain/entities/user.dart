// lib/domain/entities/user.dart
import 'package:equatable/equatable.dart';

class User extends Equatable {
  final int id;
  final String email;
  final String username;
  final String firstName;
  final String lastName;
  final String role;
  final bool isActive;
  final bool isSuperuser;
  final DateTime createdAt;
  final DateTime updatedAt;

  const User({
    required this.id,
    required this.email,
    required this.username,
    required this.firstName,
    required this.lastName,
    required this.role,
    required this.isActive,
    required this.isSuperuser,
    required this.createdAt,
    required this.updatedAt,
  });

  String get fullName => '$firstName $lastName';
  
  bool get isAdmin => role == 'admin' || isSuperuser;
  bool get isManagerOrAbove => ['admin', 'manager'].contains(role) || isSuperuser;
  bool get isClerkOrAbove => ['admin', 'manager', 'clerk'].contains(role) || isSuperuser;

  @override
  List<Object?> get props => [
        id,
        email,
        username,
        firstName,
        lastName,
        role,
        isActive,
        isSuperuser,
        createdAt,
        updatedAt,
      ];
}
