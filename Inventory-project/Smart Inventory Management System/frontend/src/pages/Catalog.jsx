import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { inventoryApi } from '../api/inventoryApi';
import { useAuth } from '../context/AuthContext';

export default function Catalog() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [categoryName, setCategoryName] = useState('');
  const [subcategoryName, setSubcategoryName] = useState('');
  const [selectedCategoryId, setSelectedCategoryId] = useState('');

  const { data: categories = [], isLoading: categoriesLoading } = useQuery({
    queryKey: ['categories'],
    queryFn: () => inventoryApi.listCategories().then((response) => response.data),
  });
  const { data: subcategories = [], isLoading: subcategoriesLoading } = useQuery({
    queryKey: ['subcategories'],
    queryFn: () => inventoryApi.listSubcategories().then((response) => response.data),
  });

  const refreshCatalog = () => {
    queryClient.invalidateQueries({ queryKey: ['categories'] });
    queryClient.invalidateQueries({ queryKey: ['subcategories'] });
  };
  const createCategory = useMutation({
    mutationFn: () => inventoryApi.createCategory({ name: categoryName.trim() }),
    onSuccess: () => { setCategoryName(''); refreshCatalog(); },
  });
  const createSubcategory = useMutation({
    mutationFn: () => inventoryApi.createSubcategory({
      category_id: Number(selectedCategoryId),
      name: subcategoryName.trim(),
    }),
    onSuccess: () => { setSubcategoryName(''); refreshCatalog(); },
  });
  const deleteCategory = useMutation({
    mutationFn: (id) => inventoryApi.deleteCategory(id),
    onSuccess: refreshCatalog,
  });
  const deleteSubcategory = useMutation({
    mutationFn: (id) => inventoryApi.deleteSubcategory(id),
    onSuccess: refreshCatalog,
  });

  const isAdmin = user?.role === 'admin';
  const isLoading = categoriesLoading || subcategoriesLoading;
  const subcategoriesByCategory = subcategories.reduce((groups, subcategory) => {
    groups[subcategory.category_id] = [...(groups[subcategory.category_id] || []), subcategory];
    return groups;
  }, {});

  const errorMessage = createCategory.error?.response?.data?.detail
    || createSubcategory.error?.response?.data?.detail
    || deleteCategory.error?.response?.data?.detail
    || deleteSubcategory.error?.response?.data?.detail;

  return (
    <div className="page-content fade-in">
      <div className="page-header inventory-header">
        <div>
          <h1 className="page-title">Electronics Catalog</h1>
          <p className="page-subtitle">Manage the category and subcategory hierarchy used by inventory.</p>
        </div>
      </div>

      {errorMessage && <div className="form-error" style={{ marginBottom: 18 }}>{errorMessage}</div>}

      {isAdmin && (
        <div className="catalog-management-grid">
          <form className="card p-6" onSubmit={(event) => { event.preventDefault(); if (categoryName.trim()) createCategory.mutate(); }}>
            <h2 className="section-title">Add category</h2>
            <label className="form-label" htmlFor="new-category">Category name</label>
            <input id="new-category" className="form-input" value={categoryName} onChange={(event) => setCategoryName(event.target.value)} placeholder="e.g. Wearables" />
            <button className="btn btn-primary mt-4" type="submit" disabled={createCategory.isPending || !categoryName.trim()}>Create category</button>
          </form>
          <form className="card p-6" onSubmit={(event) => { event.preventDefault(); if (selectedCategoryId && subcategoryName.trim()) createSubcategory.mutate(); }}>
            <h2 className="section-title">Add subcategory</h2>
            <label className="form-label" htmlFor="subcategory-parent">Parent category</label>
            <select id="subcategory-parent" className="form-select" value={selectedCategoryId} onChange={(event) => setSelectedCategoryId(event.target.value)}>
              <option value="">Select a category</option>
              {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
            </select>
            <label className="form-label mt-4" htmlFor="new-subcategory">Subcategory name</label>
            <input id="new-subcategory" className="form-input" value={subcategoryName} onChange={(event) => setSubcategoryName(event.target.value)} placeholder="e.g. Smart Rings" />
            <button className="btn btn-primary mt-4" type="submit" disabled={createSubcategory.isPending || !selectedCategoryId || !subcategoryName.trim()}>Create subcategory</button>
          </form>
        </div>
      )}

      <div className="card catalog-hierarchy-card">
        <div className="card-header-row">
          <div>
            <h2 className="section-title">Category hierarchy</h2>
            <p className="page-subtitle">{categories.length} categories, {subcategories.length} subcategories</p>
          </div>
        </div>
        {isLoading ? <div className="flex-center loader-box"><div className="spinner spinner-lg" /></div> : (
          <div className="catalog-hierarchy">
            {categories.map((category) => (
              <section className="catalog-category" key={category.id}>
                <div className="catalog-category-heading">
                  <h3>{category.name}</h3>
                  {isAdmin && <button className="btn btn-danger btn-sm" onClick={() => deleteCategory.mutate(category.id)}>Delete</button>}
                </div>
                <div className="catalog-subcategory-list">
                  {(subcategoriesByCategory[category.id] || []).map((subcategory) => (
                    <div className="catalog-subcategory" key={subcategory.id}>
                      <span>{subcategory.name}</span>
                      {isAdmin && <button className="btn btn-secondary btn-sm" onClick={() => deleteSubcategory.mutate(subcategory.id)}>Remove</button>}
                    </div>
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
