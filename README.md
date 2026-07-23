# 🧞‍♂️ AI Assistant for product discovery

*A demo showcasing how a Lebanese retail company can use Knowledge Graphs + LLMs to power customer and business insights.*

<a href="https://libanjus-kg-demo.streamlit.app/" target="_blank">
    <img src="https://static.streamlit.io/badges/streamlit_badge_black_red.svg" alt="Streamlit App" width="200" />
</a>

## 🎯 **What It Does**

For example, let's consider questions about a food products company

### For Customers:
- **Dietary Questions**: *"As a celiac, what sweet products can I get?"*
- **Product Availability**: *"Is there lactose-free fat-free milk?"*
- **Store Hours**: *"Which stores are open on Sunday afternoon?"*

### For Staff:
- **Distribution Insights**: *"Which distributors cover the most retailers in Beirut?"*
- **Product Analysis**: *"What are our most widely available products?"*

## 🚀 **Try the Live Demo**
Ask the assistant:
- *"Which products are gluten-free?"*
- *"Where can I find hummus in Achrafieh open after 6pm?"*
- *"What products are available at Spinneys Gemmayzeh?"*

<a href="https://libanjus-kg-demo.streamlit.app/" target="_blank">
    <img src="https://static.streamlit.io/badges/streamlit_badge_black_red.svg" alt="Streamlit App" width="200" />
</a>

## 📊 **Knowledge Graph Schema**
```mermaid
graph TD
    Product -- AVAILABLE_AT --> Retailer
    Product -- MANUFACTURED_AT --> Factory
    Product -- DISTRIBUTED_BY --> Distributor
    Distributor -- SUPPLIES_TO --> Retailer
    Retailer -- LOCATED_AT --> Location
    Retailer -- OPEN_AT --> TimeSlot
```

## License
[MIT](LICENSE) © Marwa Maghnie