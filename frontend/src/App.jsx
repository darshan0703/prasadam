import { BrowserRouter, Routes, Route } from "react-router-dom";
import { CartProvider } from "./context/CartContext";
import KioskViewport from "./components/KioskViewport";
import Home from "./Pages/Home";
import Categories from "./Pages/Categories";
import MenuItems from "./Pages/MenuItems";
import ProductPage from "./Pages/ProductPage";
import CartPage from "./Pages/CartPage";
import OrderCompletePage from "./Pages/OrderCompletePage";

import { UIActionProvider } from "./context/UIActionContext";
import { VoiceConversationProvider } from "./context/VoiceConversationProvider";

function App() {
  return (
    <BrowserRouter>
      <CartProvider>
        <UIActionProvider>
          <VoiceConversationProvider>
            <KioskViewport>
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/Categories" element={<Categories />} />
                <Route path="/menu-items" element={<MenuItems />} />
                <Route path="/product" element={<ProductPage />} />
                <Route path="/cart" element={<CartPage />} />
                <Route path="/order-complete" element={<OrderCompletePage />} />
              </Routes>
            </KioskViewport>
          </VoiceConversationProvider>
        </UIActionProvider>
      </CartProvider>
    </BrowserRouter>
  );
}

export default App;
