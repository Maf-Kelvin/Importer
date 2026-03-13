// lib/domain/entities/pricing.dart
import 'package:equatable/equatable.dart';

class PriceRecord extends Equatable {
  final int id;
  final int itemId;
  final int userId;
  final String method;
  final String? source;
  final double price;
  final String currency;
  final String? sourceUrl;
  final double? confidenceScore;
  final double? marginPercentage;
  final String? notes;
  final bool isActive;
  final DateTime createdAt;
  final DateTime updatedAt;

  const PriceRecord({
    required this.id,
    required this.itemId,
    required this.userId,
    required this.method,
    this.source,
    required this.price,
    required this.currency,
    this.sourceUrl,
    this.confidenceScore,
    this.marginPercentage,
    this.notes,
    required this.isActive,
    required this.createdAt,
    required this.updatedAt,
  });

  String get displayMethod {
    switch (method) {
      case 'cost_based':
        return 'Cost Based';
      case 'market_based':
        return 'Market Based';
      case 'last_sold':
        return 'Last Sold';
      default:
        return method.toUpperCase();
    }
  }

  String get displaySource {
    switch (source) {
      case 'jiji':
        return 'Jiji.ng';
      case 'ebay':
        return 'eBay';
      case 'mobile_de':
        return 'Mobile.de';
      case 'autoscout24':
        return 'AutoScout24';
      case 'bazos_cz':
        return 'Bazos.cz';
      default:
        return source ?? 'Unknown';
    }
  }

  @override
  List<Object?> get props => [
        id,
        itemId,
        userId,
        method,
        source,
        price,
        currency,
        sourceUrl,
        confidenceScore,
        marginPercentage,
        notes,
        isActive,
        createdAt,
        updatedAt,
      ];
}
