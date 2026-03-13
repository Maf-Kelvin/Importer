// lib/data/models/pricing_model.dart
import 'package:json_annotation/json_annotation.dart';
import '../../domain/entities/pricing.dart';

part 'pricing_model.g.dart';

@JsonSerializable()
class PriceRecordModel extends PriceRecord {
  const PriceRecordModel({
    required super.id,
    required super.itemId,
    required super.userId,
    required super.method,
    super.source,
    required super.price,
    required super.currency,
    super.sourceUrl,
    super.confidenceScore,
    super.marginPercentage,
    super.notes,
    required super.isActive,
    required super.createdAt,
    required super.updatedAt,
  });

  factory PriceRecordModel.fromJson(Map<String, dynamic> json) =>
      _$PriceRecordModelFromJson(json);

  Map<String, dynamic> toJson() => _$PriceRecordModelToJson(this);

  PriceRecord toEntity() => PriceRecord(
        id: id,
        itemId: itemId,
        userId: userId,
        method: method,
        source: source,
        price: price,
        currency: currency,
        sourceUrl: sourceUrl,
        confidenceScore: confidenceScore,
        marginPercentage: marginPercentage,
        notes: notes,
        isActive: isActive,
        createdAt: createdAt,
        updatedAt: updatedAt,
      );
}

@JsonSerializable()
class PricingResponse {
  @JsonKey(name: 'item_id')
  final int itemId;
  
  @JsonKey(name: 'cost_based_price')
  final double? costBasedPrice;
  
  @JsonKey(name: 'market_prices')
  final List<MarketPriceModel> marketPrices;
  
  @JsonKey(name: 'last_sold_price')
  final double? lastSoldPrice;
  
  @JsonKey(name: 'recommended_price')
  final double? recommendedPrice;
  
  @JsonKey(name: 'profit_margin')
  final double? profitMargin;
  
  @JsonKey(name: 'generated_at')
  final String generatedAt;

  const PricingResponse({
    required this.itemId,
    this.costBasedPrice,
    required this.marketPrices,
    this.lastSoldPrice,
    this.recommendedPrice,
    this.profitMargin,
    required this.generatedAt,
  });

  factory PricingResponse.fromJson(Map<String, dynamic> json) =>
      _$PricingResponseFromJson(json);

  Map<String, dynamic> toJson() => _$PricingResponseToJson(this);
}

@JsonSerializable()
class MarketPriceModel {
  final String source;
  final double price;
  final String currency;
  final String? url;
  final double confidence;
  
  @JsonKey(name: 'found_at')
  final String foundAt;

  const MarketPriceModel({
    required this.source,
    required this.price,
    required this.currency,
    this.url,
    required this.confidence,
    required this.foundAt,
  });

  factory MarketPriceModel.fromJson(Map<String, dynamic> json) =>
      _$MarketPriceModelFromJson(json);

  Map<String, dynamic> toJson() => _$MarketPriceModelToJson(this);
}
