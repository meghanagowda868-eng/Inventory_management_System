import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { inventoryApi } from '../api/inventoryApi';
import { useAuth } from '../context/AuthContext';

export default function Sales() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const isManagerOrAdmin = ['admin', 'manager'].includes(user?.role?.toLowerCase());

  // State
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [isCheckoutOpen, setIsCheckoutOpen] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [isReceiptOpen, setIsReceiptOpen] = useState(false);
  const [refundOrderId, setRefundOrderId] = useState(null);
  const [refundReason, setRefundReason] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // POS Checkout Cart State
  const [cartItems, setCartItems] = useState([]);
  const [selectedProductId, setSelectedProductId] = useState('');
  const [selectedQty, setSelectedQty] = useState(1);
  const [selectedDiscount, setSelectedDiscount] = useState(0);
  const [customerName, setCustomerName] = useState('');
  const [customerEmail, setCustomerEmail] = useState('');
  const [customerPhone, setCustomerPhone] = useState('');
  const [channel, setChannel] = useState('IN_STORE');
  const [paymentMethod, setPaymentMethod] = useState('CARD');
  const [orderNotes, setOrderNotes] = useState('');

  // Fetch Sales Orders
  const { data: orders = [], isLoading: isLoadingOrders } = useQuery({
    queryKey: ['salesOrders', statusFilter, searchTerm],
    queryFn: async () => {
      const res = await inventoryApi.listSalesOrders({
        status: statusFilter || undefined,
        search: searchTerm || undefined,
      });
      return res.data;
    },
  });

  // Fetch Sales Summary KPIs
  const { data: summary } = useQuery({
    queryKey: ['salesSummary'],
    queryFn: async () => {
      const res = await inventoryApi.getSalesSummary();
      return res.data;
    },
  });

  // Fetch Product Options for Checkout
  const { data: products = [] } = useQuery({
    queryKey: ['productOptions'],
    queryFn: async () => {
      const res = await inventoryApi.listProducts({ page: 1, limit: 100 });
      return res.data;
    },
  });

  // Create Sale Mutation
  const createSaleMutation = useMutation({
    mutationFn: (payload) => inventoryApi.createSalesOrder(payload),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['salesOrders'] });
      queryClient.invalidateQueries({ queryKey: ['salesSummary'] });
      queryClient.invalidateQueries({ queryKey: ['products'] });
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      setSuccessMsg(`Order ${res.data.order_number} created successfully! Total: $${res.data.total_amount.toFixed(2)}`);
      setIsCheckoutOpen(false);
      resetCart();
      setTimeout(() => setSuccessMsg(''), 6000);
    },
    onError: (err) => {
      setErrorMsg(err.response?.data?.detail || 'Failed to process sales order');
      setTimeout(() => setErrorMsg(''), 6000);
    },
  });

  // Refund Mutation
  const refundMutation = useMutation({
    mutationFn: ({ id, reason }) => inventoryApi.refundSalesOrder(id, reason),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['salesOrders'] });
      queryClient.invalidateQueries({ queryKey: ['salesSummary'] });
      queryClient.invalidateQueries({ queryKey: ['products'] });
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      setSuccessMsg(`Order ${res.data.order_number} refunded and inventory restored.`);
      setRefundOrderId(null);
      setRefundReason('');
      setTimeout(() => setSuccessMsg(''), 6000);
    },
    onError: (err) => {
      setErrorMsg(err.response?.data?.detail || 'Failed to refund order');
      setTimeout(() => setErrorMsg(''), 6000);
    },
  });

  const resetCart = () => {
    setCartItems([]);
    setSelectedProductId('');
    setSelectedQty(1);
    setSelectedDiscount(0);
    setCustomerName('');
    setCustomerEmail('');
    setCustomerPhone('');
    setChannel('IN_STORE');
    setPaymentMethod('CARD');
    setOrderNotes('');
  };

  const handleAddItemToCart = () => {
    if (!selectedProductId) return;
    const prod = products.find((p) => p.id === Number(selectedProductId));
    if (!prod) return;

    if (selectedQty <= 0) {
      setErrorMsg('Quantity must be greater than 0');
      return;
    }
    if (selectedQty > prod.quantity) {
      setErrorMsg(`Only ${prod.quantity} units available for ${prod.name}`);
      return;
    }

    const existingIdx = cartItems.findIndex((item) => item.product_id === prod.id);
    if (existingIdx >= 0) {
      const newQty = cartItems[existingIdx].quantity + Number(selectedQty);
      if (newQty > prod.quantity) {
        setErrorMsg(`Cannot add more. Total in cart (${newQty}) exceeds available stock (${prod.quantity})`);
        return;
      }
      const updated = [...cartItems];
      updated[existingIdx].quantity = newQty;
      updated[existingIdx].discount_percent = Number(selectedDiscount);
      setCartItems(updated);
    } else {
      setCartItems([
        ...cartItems,
        {
          product_id: prod.id,
          product_name: prod.name,
          sku: prod.sku,
          price: prod.price,
          quantity: Number(selectedQty),
          discount_percent: Number(selectedDiscount),
        },
      ]);
    }

    setSelectedProductId('');
    setSelectedQty(1);
    setSelectedDiscount(0);
    setErrorMsg('');
  };

  const handleRemoveFromCart = (index) => {
    setCartItems(cartItems.filter((_, i) => i !== index));
  };

  // Cart Totals Calculation
  const subtotal = cartItems.reduce((acc, item) => acc + item.price * item.quantity, 0);
  const discountTotal = cartItems.reduce(
    (acc, item) => acc + item.price * item.quantity * ((item.discount_percent || 0) / 100),
    0
  );
  const grandTotal = Math.max(0, subtotal - discountTotal);

  const handleCheckoutSubmit = (e) => {
    e.preventDefault();
    if (cartItems.length === 0) {
      setErrorMsg('Please add at least one product to the sale order');
      return;
    }
    if (!customerName.trim()) {
      setErrorMsg('Customer name is required');
      return;
    }

    createSaleMutation.mutate({
      customer_name: customerName.trim(),
      customer_email: customerEmail.trim() || undefined,
      customer_phone: customerPhone.trim() || undefined,
      channel,
      payment_method: paymentMethod,
      notes: orderNotes.trim() || undefined,
      items: cartItems.map((item) => ({
        product_id: item.product_id,
        quantity: item.quantity,
        discount_percent: item.discount_percent || 0,
      })),
    });
  };

  const openReceipt = (order) => {
    setSelectedOrder(order);
    setIsReceiptOpen(true);
  };

  return (
    <div className="page-container">
      {/* Header Banner */}
      <div className="page-header flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <span>🛒</span> Sales & Point of Sale (POS)
          </h2>
          <p className="text-slate-400 text-sm mt-1">
            Process direct customer transactions, manage receipts, and trace real-time stock deductions.
          </p>
        </div>
        <button
          onClick={() => setIsCheckoutOpen(true)}
          className="btn btn-primary flex items-center gap-2 px-5 py-2.5 shadow-lg shadow-indigo-500/20"
        >
          <span>＋</span> New Sale / POS Checkout
        </button>
      </div>

      {/* Alert Messages */}
      {successMsg && (
        <div className="alert alert-success mb-4 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 flex items-center gap-2">
          <span>✓</span> {successMsg}
        </div>
      )}
      {errorMsg && (
        <div className="alert alert-error mb-4 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 flex items-center gap-2">
          <span>⚠</span> {errorMsg}
        </div>
      )}

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="stat-card p-4 rounded-2xl bg-slate-800/60 border border-slate-700/60">
          <div className="text-xs text-slate-400 uppercase font-semibold">Total Revenue</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">
            ${summary ? summary.total_revenue.toLocaleString('en-US', { minimumFractionDigits: 2 }) : '0.00'}
          </div>
          <div className="text-xs text-slate-500 mt-1">Completed sale transactions</div>
        </div>

        <div className="stat-card p-4 rounded-2xl bg-slate-800/60 border border-slate-700/60">
          <div className="text-xs text-slate-400 uppercase font-semibold">Completed Orders</div>
          <div className="text-2xl font-bold text-indigo-400 mt-1">
            {summary?.completed_orders ?? 0}
          </div>
          <div className="text-xs text-slate-500 mt-1">{summary?.refunded_orders ?? 0} refunded</div>
        </div>

        <div className="stat-card p-4 rounded-2xl bg-slate-800/60 border border-slate-700/60">
          <div className="text-xs text-slate-400 uppercase font-semibold">Units Sold</div>
          <div className="text-2xl font-bold text-amber-400 mt-1">
            {summary?.total_items_sold ?? 0}
          </div>
          <div className="text-xs text-slate-500 mt-1">Items moved via sales ledger</div>
        </div>

        <div className="stat-card p-4 rounded-2xl bg-slate-800/60 border border-slate-700/60">
          <div className="text-xs text-slate-400 uppercase font-semibold">Avg. Order Value</div>
          <div className="text-2xl font-bold text-cyan-400 mt-1">
            ${summary ? summary.average_order_value.toFixed(2) : '0.00'}
          </div>
          <div className="text-xs text-slate-500 mt-1">Revenue / completed order</div>
        </div>
      </div>

      {/* Filter & Search Controls */}
      <div className="card p-4 mb-6 flex flex-wrap gap-4 items-center justify-between bg-slate-800/50 border border-slate-700/50 rounded-xl">
        <div className="flex flex-1 items-center gap-3 min-w-[280px]">
          <input
            type="text"
            placeholder="Search by Order # or Customer Name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="input input-bordered w-full bg-slate-900 border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2"
          />
        </div>
        <div className="flex items-center gap-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="select select-bordered bg-slate-900 border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2"
          >
            <option value="">All Statuses</option>
            <option value="COMPLETED">Completed</option>
            <option value="REFUNDED">Refunded</option>
            <option value="CANCELLED">Cancelled</option>
          </select>
        </div>
      </div>

      {/* Orders Table */}
      <div className="card overflow-hidden bg-slate-800/60 border border-slate-700/60 rounded-2xl shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-900/80 text-xs uppercase font-semibold text-slate-400 border-b border-slate-700">
              <tr>
                <th className="px-5 py-3">Order Number</th>
                <th className="px-5 py-3">Date & Time</th>
                <th className="px-5 py-3">Customer</th>
                <th className="px-5 py-3">Channel / Pay</th>
                <th className="px-5 py-3 text-right">Items</th>
                <th className="px-5 py-3 text-right">Total Amount</th>
                <th className="px-5 py-3 text-center">Status</th>
                <th className="px-5 py-3 text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/40">
              {isLoadingOrders ? (
                <tr>
                  <td colSpan={8} className="text-center py-8 text-slate-400">
                    Loading sales transactions...
                  </td>
                </tr>
              ) : orders.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-8 text-slate-400">
                    No sales orders found matching your search.
                  </td>
                </tr>
              ) : (
                orders.map((order) => (
                  <tr key={order.id} className="hover:bg-slate-700/20 transition">
                    <td className="px-5 py-3.5 font-mono font-medium text-indigo-400">
                      {order.order_number}
                    </td>
                    <td className="px-5 py-3.5 text-xs text-slate-400">
                      {new Date(order.created_at).toLocaleString()}
                    </td>
                    <td className="px-5 py-3.5 font-medium text-slate-200">
                      {order.customer_name}
                      {order.customer_phone && (
                        <div className="text-xs text-slate-500 font-mono">{order.customer_phone}</div>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-xs">
                      <span className="text-slate-300">{order.channel}</span>
                      <span className="text-slate-500 ml-1">({order.payment_method})</span>
                    </td>
                    <td className="px-5 py-3.5 text-right font-semibold">
                      {order.items?.length || 0}
                    </td>
                    <td className="px-5 py-3.5 text-right font-bold text-slate-100">
                      ${order.total_amount.toFixed(2)}
                    </td>
                    <td className="px-5 py-3.5 text-center">
                      <span
                        className={`inline-block px-2.5 py-1 rounded-full text-xs font-semibold ${
                          order.status === 'COMPLETED'
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                            : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                        }`}
                      >
                        {order.status}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-center flex items-center justify-center gap-2">
                      <button
                        onClick={() => openReceipt(order)}
                        className="btn btn-sm btn-ghost text-xs text-indigo-300 hover:text-indigo-200 hover:bg-slate-700/50 px-2.5 py-1 rounded"
                      >
                        Receipt
                      </button>
                      {isManagerOrAdmin && order.status === 'COMPLETED' && (
                        <button
                          onClick={() => setRefundOrderId(order.id)}
                          className="btn btn-sm btn-ghost text-xs text-rose-400 hover:text-rose-300 hover:bg-rose-900/30 px-2.5 py-1 rounded"
                        >
                          Refund
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* POS Checkout Modal */}
      {isCheckoutOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-700 flex justify-between items-center bg-slate-800/50">
              <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <span>⚡</span> Point of Sale (POS) & Checkout
              </h3>
              <button
                onClick={() => setIsCheckoutOpen(false)}
                className="text-slate-400 hover:text-slate-200 text-xl font-bold"
              >
                ✕
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-6 flex-1">
              {/* Product Selection Row */}
              <div className="bg-slate-800/40 p-4 rounded-xl border border-slate-700/60 space-y-4">
                <div className="text-sm font-semibold text-slate-300">Add Products to Sale</div>
                <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 items-end">
                  <div className="sm:col-span-5">
                    <label className="text-xs text-slate-400 mb-1 block">Select Product</label>
                    <select
                      value={selectedProductId}
                      onChange={(e) => setSelectedProductId(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2"
                    >
                      <option value="">-- Choose a Product --</option>
                      {products.map((p) => (
                        <option key={p.id} value={p.id} disabled={p.quantity <= 0}>
                          {p.name} (${p.price}) — {p.quantity > 0 ? `${p.quantity} in stock` : 'OUT OF STOCK'}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="sm:col-span-2">
                    <label className="text-xs text-slate-400 mb-1 block">Quantity</label>
                    <input
                      type="number"
                      min={1}
                      value={selectedQty}
                      onChange={(e) => setSelectedQty(Math.max(1, parseInt(e.target.value) || 1))}
                      className="w-full bg-slate-900 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2"
                    />
                  </div>

                  <div className="sm:col-span-2">
                    <label className="text-xs text-slate-400 mb-1 block">Discount %</label>
                    <input
                      type="number"
                      min={0}
                      max={100}
                      value={selectedDiscount}
                      onChange={(e) => setSelectedDiscount(Math.min(100, Math.max(0, parseFloat(e.target.value) || 0)))}
                      className="w-full bg-slate-900 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2"
                    />
                  </div>

                  <div className="sm:col-span-3">
                    <button
                      type="button"
                      onClick={handleAddItemToCart}
                      disabled={!selectedProductId}
                      className="w-full btn btn-primary py-2 text-sm font-semibold rounded-lg disabled:opacity-50"
                    >
                      Add to Cart
                    </button>
                  </div>
                </div>
              </div>

              {/* Cart Table */}
              <div>
                <div className="text-sm font-semibold text-slate-300 mb-2">Order Line Items ({cartItems.length})</div>
                {cartItems.length === 0 ? (
                  <div className="text-center py-6 border border-dashed border-slate-700 rounded-xl text-slate-500 text-sm">
                    No items in cart. Select products above to start sale checkout.
                  </div>
                ) : (
                  <div className="border border-slate-700 rounded-xl overflow-hidden">
                    <table className="w-full text-left text-xs text-slate-300">
                      <thead className="bg-slate-800 text-slate-400 border-b border-slate-700">
                        <tr>
                          <th className="px-4 py-2">Item</th>
                          <th className="px-3 py-2 text-right">Price</th>
                          <th className="px-3 py-2 text-right">Qty</th>
                          <th className="px-3 py-2 text-right">Disc%</th>
                          <th className="px-4 py-2 text-right">Line Total</th>
                          <th className="px-3 py-2 text-center">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-700/50 bg-slate-900/50">
                        {cartItems.map((item, idx) => {
                          const raw = item.price * item.quantity;
                          const disc = raw * ((item.discount_percent || 0) / 100);
                          const total = raw - disc;
                          return (
                            <tr key={idx}>
                              <td className="px-4 py-2.5 font-medium text-slate-200">
                                {item.product_name}
                                <span className="text-slate-500 ml-1 text-[11px]">({item.sku})</span>
                              </td>
                              <td className="px-3 py-2.5 text-right">${item.price.toFixed(2)}</td>
                              <td className="px-3 py-2.5 text-right font-semibold">{item.quantity}</td>
                              <td className="px-3 py-2.5 text-right text-amber-400">
                                {item.discount_percent > 0 ? `${item.discount_percent}%` : '-'}
                              </td>
                              <td className="px-4 py-2.5 text-right font-bold text-slate-100">${total.toFixed(2)}</td>
                              <td className="px-3 py-2.5 text-center">
                                <button
                                  type="button"
                                  onClick={() => handleRemoveFromCart(idx)}
                                  className="text-rose-400 hover:text-rose-300 font-bold"
                                >
                                  ✕
                                </button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Customer & Payment Form */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-slate-800/30 p-4 rounded-xl border border-slate-700/40">
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Customer Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. John Doe"
                    value={customerName}
                    onChange={(e) => setCustomerName(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2"
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Customer Email</label>
                  <input
                    type="email"
                    placeholder="customer@email.com"
                    value={customerEmail}
                    onChange={(e) => setCustomerEmail(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2"
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Sales Channel</label>
                  <select
                    value={channel}
                    onChange={(e) => setChannel(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2"
                  >
                    <option value="IN_STORE">In Store (Counter POS)</option>
                    <option value="ONLINE">Online Store</option>
                    <option value="B2B">B2B / Wholesale</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Payment Method</label>
                  <select
                    value={paymentMethod}
                    onChange={(e) => setPaymentMethod(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2"
                  >
                    <option value="CARD">Credit / Debit Card</option>
                    <option value="CASH">Cash</option>
                    <option value="UPI">UPI / Digital QR</option>
                    <option value="BANK_TRANSFER">Bank Transfer / Net Banking</option>
                  </select>
                </div>
              </div>

              {/* Order Calculations Summary */}
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2 text-sm">
                <div className="flex justify-between text-slate-400">
                  <span>Subtotal:</span>
                  <span>${subtotal.toFixed(2)}</span>
                </div>
                {discountTotal > 0 && (
                  <div className="flex justify-between text-amber-400">
                    <span>Discount Applied:</span>
                    <span>-${discountTotal.toFixed(2)}</span>
                  </div>
                )}
                <div className="border-t border-slate-800 pt-2 flex justify-between text-lg font-bold text-slate-100">
                  <span>Grand Total:</span>
                  <span className="text-emerald-400">${grandTotal.toFixed(2)}</span>
                </div>
              </div>
            </div>

            <div className="px-6 py-4 border-t border-slate-700 flex justify-end gap-3 bg-slate-800/50">
              <button
                type="button"
                onClick={() => setIsCheckoutOpen(false)}
                className="btn btn-ghost text-slate-300 hover:bg-slate-700 px-4 py-2 rounded-lg text-sm"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleCheckoutSubmit}
                disabled={cartItems.length === 0 || !customerName.trim() || createSaleMutation.isPending}
                className="btn btn-primary px-6 py-2 rounded-lg font-bold text-sm shadow-lg shadow-indigo-500/20 disabled:opacity-50"
              >
                {createSaleMutation.isPending ? 'Processing...' : `Confirm & Charge $${grandTotal.toFixed(2)}`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Order Receipt Modal */}
      {isReceiptOpen && selectedOrder && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-lg p-6 shadow-2xl space-y-4">
            <div className="flex justify-between items-start border-b border-slate-700 pb-3">
              <div>
                <h3 className="text-lg font-bold text-slate-100">Sale Receipt / Invoice</h3>
                <div className="text-xs text-indigo-400 font-mono font-bold mt-0.5">{selectedOrder.order_number}</div>
              </div>
              <button
                onClick={() => setIsReceiptOpen(false)}
                className="text-slate-400 hover:text-slate-200 text-xl font-bold"
              >
                ✕
              </button>
            </div>

            <div className="text-xs text-slate-400 space-y-1">
              <div><strong className="text-slate-300">Date:</strong> {new Date(selectedOrder.created_at).toLocaleString()}</div>
              <div><strong className="text-slate-300">Customer:</strong> {selectedOrder.customer_name}</div>
              <div><strong className="text-slate-300">Payment:</strong> {selectedOrder.payment_method} ({selectedOrder.channel})</div>
              <div><strong className="text-slate-300">Status:</strong> {selectedOrder.status}</div>
            </div>

            <div className="border border-slate-700 rounded-xl overflow-hidden">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-800 text-slate-400 border-b border-slate-700">
                  <tr>
                    <th className="px-3 py-2">Item</th>
                    <th className="px-2 py-2 text-right">Qty</th>
                    <th className="px-2 py-2 text-right">Price</th>
                    <th className="px-3 py-2 text-right">Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {selectedOrder.items?.map((it) => (
                    <tr key={it.id}>
                      <td className="px-3 py-2 font-medium">{it.product_name || `Product #${it.product_id}`}</td>
                      <td className="px-2 py-2 text-right">{it.quantity}</td>
                      <td className="px-2 py-2 text-right">${it.unit_price.toFixed(2)}</td>
                      <td className="px-3 py-2 text-right font-bold text-slate-100">${it.line_total.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="border-t border-slate-700 pt-3 space-y-1 text-xs">
              <div className="flex justify-between text-slate-400">
                <span>Subtotal:</span>
                <span>${selectedOrder.subtotal.toFixed(2)}</span>
              </div>
              {selectedOrder.discount_amount > 0 && (
                <div className="flex justify-between text-amber-400">
                  <span>Discount:</span>
                  <span>-${selectedOrder.discount_amount.toFixed(2)}</span>
                </div>
              )}
              <div className="flex justify-between text-sm font-bold text-slate-100 pt-1 border-t border-slate-800">
                <span>Total Paid:</span>
                <span className="text-emerald-400">${selectedOrder.total_amount.toFixed(2)}</span>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setIsReceiptOpen(false)}
                className="btn btn-primary w-full py-2 rounded-lg text-xs font-semibold"
              >
                Close Receipt
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Refund Confirmation Modal */}
      {refundOrderId && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-rose-400 flex items-center gap-2">
              <span>⚠</span> Confirm Order Refund
            </h3>
            <p className="text-xs text-slate-300">
              Refunding this order will mark it as REFUNDED and automatically return all items back into active inventory.
            </p>

            <div>
              <label className="text-xs text-slate-400 mb-1 block">Reason for Refund *</label>
              <textarea
                rows={3}
                required
                placeholder="e.g. Customer returned goods, damaged in transit..."
                value={refundReason}
                onChange={(e) => setRefundReason(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-lg p-2.5"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => {
                  setRefundOrderId(null);
                  setRefundReason('');
                }}
                className="btn btn-ghost text-xs text-slate-300 px-3 py-1.5 rounded"
              >
                Cancel
              </button>
              <button
                onClick={() => refundMutation.mutate({ id: refundOrderId, reason: refundReason })}
                disabled={!refundReason.trim() || refundMutation.isPending}
                className="btn btn-error text-xs font-bold px-4 py-1.5 rounded bg-rose-600 hover:bg-rose-500 text-white disabled:opacity-50"
              >
                {refundMutation.isPending ? 'Processing...' : 'Confirm Refund & Restock'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
