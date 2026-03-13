// lib/data/models/item_model.dart
import 'package:json_annotation/json_annotation.dart';
import '../../domain/entities/item.dart';
import 'pricing_model.dart';

part 'item_model.g.dart';

@JsonSerializable()
class ItemModel extends Item {
  const ItemModel({
    required super.id,
    required super.containerId,
    required super.name,
    super.description,
    required super.category,
    required super.condition,
    required super.purchasePrice,
    required super.purchaseCurrency,
    super.purchaseDate,
    required super.fxRateToUsd,
    required super.purchasePriceUsd,
    required super.weight,
    super.volume,
    super.allocatedCost,
    super.landedCost,
    super.recommendedPrice,
    super.sellingPrice,
    required super.sold,
    super.soldDate,
    required super.createdAt,
    required super.updatedAt,
    super.priceRecords,
    super.profitMargin,
    super.profitAmount,
  });

  factory ItemModel.fromJson(Map<String, dynamic> json) =>
      _$ItemModelFromJson(json);

  Map<String, dynamic> toJson() => _$ItemModelToJson(this);

  Item toEntity() => Item(
        id: id,
        containerId: containerId,
        name: name,
        description: description,
        category: category,
        condition: condition,
        purchasePrice: purchasePrice,
        purchaseCurrency: purchaseCurrency,
        purchaseDate: purchaseDate,
        fxRateToUsd: fxRateToUsd,
        purchasePriceUsd: purchasePriceUsd,
        weight: weight,
        volume: volume,
        allocatedCost: allocatedCost,
        landedCost: landedCost,
        recommendedPrice: recommendedPrice,
        sellingPrice: sellingPrice,
        sold: sold,
        soldDate: soldDate,
        createdAt: createdAt,
        updatedAt: updatedAt,
        priceRecords: priceRecords?.map((e) => (e as PriceRecordModel).toEntity()).toList(),
        profitMargin: profitMargin,
        profitAmount: profitAmount,
      );
}

@JsonSerializable()
class CreateItemRequest {
  @JsonKey(name: 'container_id')
  final int containerId;
  
  final String name;
  final String? description;
  final String category;
  final String condition;
  
  @JsonKey(name: 'purchase_price')
  final double purchasePrice;
  
  @JsonKey(name: 'purchase_currency')
  final String purchaseCurrency;
  
  @JsonKey(name: 'purchase_date')
  final String? purchaseDate;
  
  final double weight;
  final double? volume;

  const CreateItemRequest({
    required this.containerId,
    required this.name,
    this.description,
    required this.category,
    required this.condition,
    required this.purchasePrice,
    required this.purchaseCurrency,
    this.purchaseDate,
    required this.weight,
    this.volume,
  });

  factory CreateItemRequest.fromJson(Map<String, dynamic> json) =>
      _$CreateItemRequestFromJson(json);

  Map<String, dynamic> toJson() => _$CreateItemRequestToJson(this);
}