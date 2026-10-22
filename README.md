# Stage 05: Persistent memory (Challenge A)

Stage này lưu quy ước dự án trong JSON để agent dùng lại giữa các conversation. Harness đọc `workspace/memory/memory.json` khi tạo system prompt cho mỗi model request. `current_conventions` chứa quy ước còn hiệu lực; `history` là log bất biến theo từng lần thêm, đổi hoặc ngừng áp dụng, có timestamp UTC cùng snapshot before/after.

## Chạy

Từ thư mục gốc của repository `BTVN07-ChallengeA`:

```bash
uv sync --locked
cp -n .env.example .env
```

Trong `.env`, chọn Gemini native:

```dotenv
MODEL_PROVIDER=google
GOOGLE_API_KEY=...     # có thể dùng GEMINI_API_KEY thay thế
MODEL_NAME=gemini-3.5-flash-lite
```

Không cần `OPENAI_BASE_URL` cho adapter Google native. Nếu `.env` cũ có URL `https://generativelanguage.googleapis.com/v1beta/openai/`, code tự nhận diện Gemini và dùng khóa `GOOGLE_API_KEY`, `GEMINI_API_KEY`, hoặc cuối cùng `OPENAI_API_KEY` để tương thích.

Với endpoint OpenAI-compatible khác, đặt `MODEL_PROVIDER=openai`, rồi điền `OPENAI_API_KEY`, `MODEL_NAME` và tùy chọn `OPENAI_BASE_URL`.

Sau đó chạy:

```bash
uv run streamlit run app.py
```

Nếu chạy lệnh từ thư mục khác, thay đường dẫn tuyệt đối bên dưới bằng nơi bạn clone repository:

```bash
uv run --project /path/to/BTVN07-ChallengeA streamlit run /path/to/BTVN07-ChallengeA/app.py
```

## Prompts bám sát Challenge A

### 0. Khởi tạo hoặc làm rõ một quy ước

Nếu muốn dùng quy ước mẫu đã có trong JSON, không cần prompt bước này. Nếu muốn kiểm tra việc cập nhật bằng prompt, gửi:

> Hãy nhớ quy ước API của dự án: mọi endpoint API mới dùng prefix `/api/v1`; tên trường JSON dùng `camelCase`. Phạm vi áp dụng là API mới.

Agent nên gọi `update_project_memory` cho từng quy ước mới/cần cập nhật. Mở `workspace/memory/memory.json` hoặc panel **Persistent memory đã nạp** để kiểm tra nội dung và timestamp do tool tạo.

### 1. Chứng minh session mới vẫn dùng quy ước đã thống nhất

Nhấn **Cuộc trò chuyện mới**, rồi gửi:

> Thiết kế endpoint đăng nhập mới và cho một ví dụ JSON response. Hãy áp dụng quy ước hiện hành của dự án. Nêu rõ endpoint path và cách viết tên các field.

Kết quả mong đợi trước khi đổi quy ước: path bắt đầu bằng `/api/v1` và JSON fields dùng `camelCase`. Trong panel, kiểm tra `current_conventions` nằm trong memory; trong snapshot request, kiểm tra system prompt chứa JSON đã inject.

### 2. Chứng minh session sau dùng quy ước mới

Trong conversation, gửi yêu cầu thay đổi rõ ràng:

> Cập nhật quy ước đặt tên field JSON: từ nay API mới dùng `snake_case` thay cho `camelCase`. Giữ nguyên quy ước endpoint prefix `/api/v1`. Đây là quy ước chính thức cho API mới.

Agent nên cập nhật quy ước có ID `json_field_naming`, giữ nguyên quy ước prefix, và tạo event `update` trong `history` có `changed_at`, `before` là `camelCase`, `after` là `snake_case`.

Nhấn **Cuộc trò chuyện mới**, rồi gửi lại prompt thiết kế endpoint ở bước 1. Kết quả mong đợi là prefix `/api/v1` vẫn được giữ và fields dùng `snake_case`. Trong JSON, `current_conventions` phải có phiên bản mới; `history` phải lưu phiên bản cũ cùng thời điểm cập nhật.

### 3. Kiểm tra log khi được hỏi

> Quy ước đặt tên field JSON trước khi cập nhật là gì, quy ước mới là gì, và hệ thống ghi nhận thay đổi lúc nào?

Agent nên phân biệt quy ước hiện hành với bản cũ trong `history` và trích timestamp `changed_at` từ JSON, không tự đoán ngày giờ.

## JSON schema và cách cập nhật

- `schema_version`: phiên bản schema dữ liệu.
- `updated_at`: thời điểm gần nhất file được cập nhật, UTC.
- `current_conventions`: các quy ước hiện hành, mỗi mục có `id`, `title`, `content`, `scope`, `created_at`, `updated_at`.
- `history`: log các sự kiện `add`, `update`, `remove`; mỗi sự kiện có `changed_at`, `reason`, `user_request`, `before`, `after`.

Agent được hướng dẫn nhận diện ý định lưu/thêm, cập nhật/đổi, hoặc bỏ quy ước. Nếu prompt chỉ hỏi quy ước hiện tại hoặc yêu cầu làm theo quy ước, agent không ghi memory. Nếu quy ước/giá trị/phạm vi chưa rõ, agent hỏi phần thiếu trước khi ghi. Thời điểm được tạo bởi tool, không phụ thuộc ngày giờ model tự sinh. Các cập nhật dùng ghi file atomic; JSON hỏng hoặc schema lạ khiến tool từ chối ghi đè để giữ dữ liệu.

File mẫu workspace mới là `fixtures/memory/memory.json`. Dữ liệu mẫu hiện tại chuyển hai quy ước cũ từ Markdown sang JSON; thời gian ban đầu là `null` vì không có timestamp nguồn. `uv run python reset_workspace.py` khôi phục fixtures và xóa log trong workspace.
