// lib/presentation/screens/containers/container_list_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:go_router/go_router.dart';
import '../../widgets/navigation/bottom_nav_bar.dart';
import '../../widgets/navigation/drawer_menu.dart';
import '../../widgets/common/loading_widget.dart';
import '../../widgets/common/error_widget.dart';
// lib/presentation/screens/containers/container_list_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:go_router/go_router.dart';
import '../../widgets/navigation/bottom_nav_bar.dart';
import '../../widgets/navigation/drawer_menu.dart';
import '../../widgets/common/loading_widget.dart';
import '../../widgets/common/error_widget.dart';
import 'widgets/container_card.dart';
import '../../../core/utils/responsive.dart';

class ContainerListScreen extends ConsumerStatefulWidget {
  const ContainerListScreen({super.key});

  @override
  ConsumerState<ContainerListScreen> createState() => _ContainerListScreenState();
}

class _ContainerListScreenState extends ConsumerState<ContainerListScreen> {
  final _searchController = TextEditingController();
  String _searchQuery = '';
  String _selectedFilter = 'All';

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Containers'),
        actions: [
          IconButton(
            icon: const Icon(Icons.filter_list),
            onPressed: _showFilterDialog,
          ),
        ],
      ),
      drawer: Responsive.isMobile(context) ? const DrawerMenu() : null,
      body: Column(
        children: [
          // Search bar
          Padding(
            padding: EdgeInsets.all(16.w),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Search containers...',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _searchQuery.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _searchController.clear();
                          setState(() {
                            _searchQuery = '';
                          });
                        },
                      )
                    : null,
              ),
              onChanged: (value) {
                setState(() {
                  _searchQuery = value;
                });
              },
            ),
          ),

          // Filter chips
          _buildFilterChips(),

          // Container list
          Expanded(
            child: _buildContainerList(),
          ),
        ],
      ),
      bottomNavigationBar: Responsive.isMobile(context)
          ? const BottomNavBar(currentIndex: 1)
          : null,
      floatingActionButton: FloatingActionButton(
        onPressed: () => context.go('/containers/create'),
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildFilterChips() {
    final filters = ['All', 'Active', 'Shipped', 'Completed'];

    return Container(
      height: 48.h,
      padding: EdgeInsets.symmetric(horizontal: 16.w),
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        itemCount: filters.length,
        itemBuilder: (context, index) {
          final filter = filters[index];
          final isSelected = _selectedFilter == filter;

          return Padding(
            padding: EdgeInsets.only(right: 8.w),
            child: FilterChip(
              label: Text(filter),
              selected: isSelected,
              onSelected: (selected) {
                setState(() {
                  _selectedFilter = filter;
                });
              },
            ),
          );
        },
      ),
    );
  }

  Widget _buildContainerList() {
    // Mock data - replace with actual provider
    final containers = _getFilteredContainers();

    if (containers.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.inventory_2_outlined,
              size: 64.w,
              color: Theme.of(context).colorScheme.onSurface.withOpacity(0.3),
            ),
            SizedBox(height: 16.h),
            Text(
              'No containers found',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            SizedBox(height: 8.h),
            Text(
              'Create your first container to get started',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                  ),
            ),
            SizedBox(height: 24.h),
            ElevatedButton.icon(
              onPressed: () => context.go('/containers/create'),
              icon: const Icon(Icons.add),
              label: const Text('Create Container'),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _handleRefresh,
      child: ListView.builder(
        padding: EdgeInsets.all(16.w),
        itemCount: containers.length,
        itemBuilder: (context, index) {
          final container = containers[index];
          return Padding(
            padding: EdgeInsets.only(bottom: 12.h),
            child: ContainerCard(
              container: container,
              onTap: () => context.go('/containers/${container['id']}'),
            ),
          );
        },
      ),
    );
  }

  Future<void> _handleRefresh() async {
    // Implement refresh logic
    await Future.delayed(const Duration(seconds: 1));
  }

  List<Map<String, dynamic>> _getFilteredContainers() {
    // Mock data - replace with actual data from provider
    final allContainers = [
      {
        'id': 1,
        'name': 'CONT-2024-001',
        'type': '40ft',
        'status': 'Shipped',
        'itemCount': 25,
        'soldCount': 8,
        'totalValue': 12500.0,
        'profit': 3200.0,
        'createdAt': DateTime.now().subtract(const Duration(days: 5)),
        'mscNumber': 'MSCU123456',
      },
      {
        'id': 2,
        'name': 'CONT-2024-002',
        'type': '20ft',
        'status': 'Active',
        'itemCount': 15,
        'soldCount': 0,
        'totalValue': 8900.0,
        'profit': 0.0,
        'createdAt': DateTime.now().subtract(const Duration(days: 2)),
        'mscNumber': null,
      },
      {
        'id': 3,
        'name': 'CONT-2024-003',
        'type': '40ft',
        'status': 'Completed',
        'itemCount': 30,
        'soldCount': 30,
        'totalValue': 18500.0,
        'profit': 5200.0,
        'createdAt': DateTime.now().subtract(const Duration(days: 20)),
        'mscNumber': 'MSCU789012',
      },
    ];

    // Apply search filter
    var filtered = allContainers.where((container) {
      if (_searchQuery.isEmpty) return true;
      return container['name']
              .toString()
              .toLowerCase()
              .contains(_searchQuery.toLowerCase()) ||
          (container['mscNumber']?.toString().toLowerCase().contains(_searchQuery.toLowerCase()) ?? false);
    }).toList();

    // Apply status filter
    if (_selectedFilter != 'All') {
      filtered = filtered.where((container) {
        return container['status'] == _selectedFilter;
      }).toList();
    }

    return filtered;
  }

  void _showFilterDialog() {
    showModalBottomSheet(
      context: context,
      builder: (context) => Container(
        padding: EdgeInsets.all(24.w),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Filter Containers',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            SizedBox(height: 16.h),
            const Text('Status'),
            SizedBox(height: 8.h),
            Wrap(
              spacing: 8.w,
              children: ['All', 'Active', 'Shipped', 'Completed']
                  .map((status) => FilterChip(
                        label: Text(status),
                        selected: _selectedFilter == status,
                        onSelected: (selected) {
                          setState(() {
                            _selectedFilter = status;
                          });
                          Navigator.pop(context);
                        },
                      ))
                  .toList(),
            ),
            SizedBox(height: 24.h),
          ],
        ),
      ),
    );
  }
}